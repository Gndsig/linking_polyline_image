#%%
import numpy as np
from shapely.geometry import LineString
from shapely.geometry import Polygon
import shapely.wkt
import functools
import glob

import matplotlib.pyplot as plt
import cv2
from PIL import Image, ImageDraw


class TileSegment:
    def __init__(self):
        pass
    
# 仕様を迷い中。クラスに完全にインスタンスを保存していくか、インスタンス依存をなくすか。
# コンストラクタが微妙な仕様になってる、いるかなこれ？
# そして、タイルセグメントのクラスをどう扱うか。迷い中。

# あと、numpyでいくのか、リストでいくのかの仕様が微妙に統一されてない。暇なときに直す。

# やること
# 順番を直して、誤差を修正する。
# タイルをくっつけるverを作る。


class LinkingPolylineImage:
    
    # constructor for WKT
    def __init__(self, zoom=18, TILE_SIZE=(256,256)):
        """
        wkt_polyline (str or shapely.geometry.LineString) : WKT string or LineString object.
        For example, 'LINESTRING(139.07730102539062 36.00022956359412, 139.0814208984375 35.98022880246021)'
        ,or shapely.geometry.LineString([(139.07455444335938, 35.9913409624497), (139.07730102539062, 35.99356320664446)])
        
        zoom (int)[0-18] : zoom level.
        TILE_SIZE (tuple of int) : The tile size(px). Probably, (256, 256).
        """
        
        self.zoom = zoom
        self.TILE_SIZE=TILE_SIZE
        
        # convert polyline unit latitude and longitude to pixel

    # ------------- convert latitude and longitude to XYZtile or vice versa ----------------
    def check_unit(self, coordinate):
        """
        coordinate (tuple or list of np.array of float) : coordinate. xy order. For example, (140.087099, 36.104665) 

        return (bool): if coordinate is longtude and latitude, return True. Else if, coordinate is pixle return False 
        """
    
        np_shape = np.array(coordinate).shape
        np_shape_rear = np.array(coordinate[1]).shape

        def check_latlng(coordinate):
            # check coordinate is longtude and latitude
            if all([-180 <= coord and coord <= 180 for coord in coordinate]):
                return True
            else:
                return False

        if len(np_shape)==2:
            # if coordinate is multiple coordinates ex. [[2,2],[2,2]]
            is_latlngs = list(map(check_latlng, coordinate))
            is_latlng = all(is_latlngs)
        else:
            if len(np_shape_rear)==0:
                # if coordinate is single coordinate ex. [1,1]
                is_latlng = check_latlng(coordinate)              
            elif len(np_shape_rear)==2:
                # if coordinate is bounds ex. [0, np.array([[1,1],[2,2]]) ]
                print('This instance is bounds ex. [ theta, np.array([[1,1],[2,2]])]')
                is_latlngs = list(map(check_latlng, coordinate[1]))
                is_latlng = all(is_latlngs)
            else:
                # other
                raise ValueError('Input must be coordinate ex. [1,1] or [[2,2],[2,2]] [0, np.array([[2,2],[2,2]])],')

        return is_latlng

    def latlng_to_pixel(self,coordinate, zoom=18, is_round=False):
        """latitude and longitude convert to pixel coordinate
        pixel coordinate explanation:https://www.trail-note.net/tech/coordinate/
        zoom (int)[0-18]: zoom level. Coordinate convert to 2**zoom magnification.
        coordinate (tuple of float) : longitude and latitude coordinate. xy order. For example, (140.087099, 36.104665)
        is_round (bool) : If True, round returns coordinate
        
        returns : (x_pixel, y_pixel)
        """
        is_latlng = self.check_unit(coordinate)  # check coordinate is longtude and latitude
        if not is_latlng:
            raise ValueError('coordinate is not longtude and latitude')
        
        latitude = coordinate[0]
        longtitude = coordinate[1]
        x_pixel = 2**(zoom+7)*(latitude/180 + 1)
        L=85.05112878
        y_pixel = 2**(zoom+7)/np.pi * (-np.arctanh(np.sin(np.pi/180*longtitude))+np.arctanh(np.sin(np.pi/180*L)))
        
        if is_round:  
            x_pixel = round(x_pixel)
            y_pixel = round(y_pixel)
        
        return x_pixel, y_pixel
    
    def pixel_to_tile(self,pixel_coordinate, is_remainder=True, TILE_SIZE='self'):
        """pixel coordinate convert to tile coordinate
        tile coordinate explanation:https://www.trail-note.net/tech/coordinate/
        pixel_coordinate (tuple of float) : longitude and latitude coordinate. xy order. For example, (140.087099, 36.104665)
        is_remainder (bool) : Pixel convert to tile, we get remainder. Remainder show coordinate in a tile. If True, return this reminder.
        
        returns : (x_tile, y_tile)
        if is_remainder : (x_tile, y_tile, x_in_tile, y_in_tile)
        """        
        if TILE_SIZE=='self' and hasattr(self, 'TILE_SIZE'):
            TILE_SIZE = self.TILE_SIZE
        elif TILE_SIZE=='self' and not hasattr(self, 'TILE_SIZE'):
            raise KeyError('TILE_SIZE is not found. Please input TILE_SIZE or in class instance')
        x_tile = pixel_coordinate[0] // TILE_SIZE[0]
        y_tile = pixel_coordinate[1] // TILE_SIZE[1]
        
        if is_remainder:
            x_in_tile = pixel_coordinate[0] % TILE_SIZE[0]
            y_in_tile = pixel_coordinate[1] % TILE_SIZE[1]
            return x_tile, y_tile, x_in_tile, y_in_tile
        
        return x_tile, y_tile
    
    def latlng_to_tile(self,coordinate, zoom=18, is_remainder=True, is_round=False, TILE_SIZE='self'):
        """atitude and longitude convert to tile coordinate
        tile coordinate explanation:https://www.trail-note.net/tech/coordinate/
        coordinate (tuple of float) : longitude and latitude coordinate. xy order. For example, (140.087099, 36.104665)
        zoom (int)[0-18]: zoom level. Coordinate convert to 2**zoom magnification.
        is_remainder (bool) : Pixel convert to tile, we get remainder. Remainder show coordinate in a tile. If True, return this reminder.
        is_round (bool) : If True, round returns at stage pixel coordinate.
        
        returns : (x_tile, y_tile)
        if is_remainder : (x_tile, y_tile, x_in_tile, y_in_tile)
        """
        pixel_coordinate = self.latlng_to_pixel(coordinate, zoom=zoom, is_round=is_round)
        tile_coordinate = self.pixel_to_tile(pixel_coordinate, is_remainder=is_remainder, TILE_SIZE=TILE_SIZE)
        
        return tile_coordinate
    

    def pixel_to_latlng(self, pixel_coordinate, zoom=18):
        """pixel coordinate convert to latitude and longitude
        pixel coordinate explanation : https://www.trail-note.net/tech/coordinate/
        pixel_coordinate (tuple of float) : pixel coordinate. xy order. For example, (59668600, 26328600)
        zoom (int)[0-18] : zoom level. Coordinate convert to 2**zoom magnification.

        returns : (longitude, latitude)
        """
        is_latlng = self.check_unit(coordinate)  # check coordinate is longtude and latitude
        if is_latlng:
            raise ValueError('coordinate is not pixel')
        
        x_pixel = pixel_coordinate[0]
        y_pixel = pixel_coordinate[1]
        L=85.05112878
        longitude = 180 * (x_pixel/(2**(zoom+7)) - 1)
        latitude = 180/np.pi * np.arcsin(np.tanh( -np.pi/(2**(zoom+7))*y_pixel + np.arctanh(np.sin(np.pi/180*L))))
        
        return longitude, latitude
    
    def tile_to_pixel(self,tile_coordinate, TILE_SIZE='self'):
        """pixel coordinate convert to pixel coordinate.
        pixel coordinate explanation : https://www.trail-note.net/tech/coordinate/
        warning :: pixel coordinate is y axis inversion.
        pixel_coordinate (tuple of float) : pixel coordinate. xy order. For example, (59668600, 26328600)
        zoom (int)[0-18] : zoom level. Coordinate convert to 2**zoom magnification.

        returns : (longitude, latitude)
        """
        if TILE_SIZE=='self' and hasattr(self, 'TILE_SIZE'):
            TILE_SIZE = self.TILE_SIZE
        elif TILE_SIZE=='self' and not hasattr(self, 'TILE_SIZE'):
            raise KeyError('TILE_SIZE is not found. Please input TILE_SIZE or in class instance')

        len_tile_coordinate = len(tile_coordinate)
        if len_tile_coordinate==2:
            is_remainder=False
        elif len_tile_coordinate==4:
            is_remainder=True
        else:
            raise ValueError('tile_coordinate is tuple of (x_tile, y_tile) or (x_tile, y_tile, x_in_tile, y_in_tile)')
        
        x_tile = tile_coordinate[0]
        y_tile = tile_coordinate[1]
        
        if not is_remainder:
            x_pixel = x_tile * TILE_SIZE[0]
            y_pixel = y_tile * TILE_SIZE[1]
        else:
            x_in_tile = tile_coordinate[2]
            y_in_tile = tile_coordinate[3]
            x_pixel = x_tile * TILE_SIZE[0] + x_in_tile
            y_pixel = y_tile * TILE_SIZE[1] + y_in_tile
        
        return x_pixel, y_pixel

    def tile_to_latlng(self,tile_coordinate, zoom=18, TILE_SIZE='self'):
        """atitude and longitude convert to tile coordinate
        tile coordinate explanation:https://www.trail-note.net/tech/coordinate/
        tile_coordinate (tuple of float) : tile coordinate. For example, (233080.0, 102845.0) or (233080.0, 102845.0, 79.98595982044935, 239.97896275669336)
        zoom (int)[0-18]: zoom level. Coordinate convert to 2**zoom magnification.
        
        returns : (x_tile, y_tile)
        """
        pixel_coordinate = self.tile_to_pixel(tile_coordinate, TILE_SIZE=TILE_SIZE)
        tile_coordinate = self.pixel_to_latlng(pixel_coordinate, zoom=zoom)
        
        return tile_coordinate
    
    
    def unit_change(self, coords, unit, zoom=18, is_round=False):
        """
        Followed unit, coords unit changes longtude and latitude to pixel or pixel to langtude and latitude.
        unit (list of str) ex.['latlng','pixel'] : input unit is 0th in list, output unit is 1th in list.
        coords (list or np.array) : coordinate. ex. np.array([[1,1], [2,2]]) 
        return : Coords changed unit.
        """
    
        if unit[0]==unit[1]:
            pass
        elif unit[0]=='latlng' and unit[1]=='pixel':
            coords = tuple(list(map(functools.partial(self.latlng_to_pixel, zoom=zoom,is_round=False), coords)))
        elif unit[0]=='pixel' and unit[1]=='latlng':
            coords = tuple(list(map(functools.partial(self.pixel_to_latlng, zoom=zoom), coords)))
        else:
            raise ValueError('unit is "pixel" or "latlng" of 2 pieces list ex, ["latlng","pixel"]')
            
        return coords
    
    # ------------- Calculation Minimum Bounding Rectangle aligned xy axis ----------------
    
    def xy_aligned(self, polyline, minimum=[], buff=[], unit=['latlng','pixel'], form='rectangle', zoom=18):
        """function to Minimum Bounding Rectangle aligned xy axis.
        polyline (shapely.geometry.LineString) : LineString object. If default, use class instance.
        
        minimum (list of [x_min,y_min]) : Minimum width of Minimum Bounding Rectangle. Unit follows output unit.
        buff (list of [x_min, y_min]) : A rectangle buffer. Unit follows output unit.
        
        unit (list of str) [['latlng', 'pixel'], ['pixel', 'pixel'] ] : The first in the list shows the unit of input.
        THe second in the list shows the unit of output. And minimum unit and buff unit follows the second in the list.
        If unit is ['latlng','pixel'], the inputed polyline unit is longtude and latitude, and return unit is pixel and minimum unit is pixel, 
        
        form (str)['minmax', 'rectangle'] : If 'minmax', return np.array([[x_min, y_min], [x_max, y_max]]).
        If 'rectangle', return [theta(=0), np.array([[x_min,y_min],[x_max,y_min],[x_max,y_max],[x_min, y_max]]) ]
        Theta is angle[rad] from x axis, this case is 0.
        
        
        Finaly, the unit of minimum and return should be unified.
        Warning, If unit is "latlng", later convert "latlng" to "pixel", point of rectangle is a little shift, no more parallelograms.
        
        If width < minimum, width=minimum and Rectangle is helf width from center point.
        """

        #if polyline=='self' and hasattr(self, 'polyline'):
        #    polyline = self.polyline
        #elif polyline=='self' and not hasattr(self, 'polyline'):
        #    raise KeyError('polyline is not found. Please input polyline or in class instance')

        if isinstance(polyline, str):
            polyline = shapely.wkt.loads(polyline)


        raw_bounds = polyline.bounds  # (x_min, y_min, xmax, y_max)
        raw_bounds = (raw_bounds[0], raw_bounds[1]), (raw_bounds[2],raw_bounds[3])

        raw_bounds = self.unit_change(raw_bounds, unit=unit,zoom=zoom, is_round=False)

        #if unit[0]==unit[1]:
        #    pass
        #elif unit[0]=='latlng' and unit[1]=='pixel':
        #    raw_bounds = tuple(list(map(functools.partial(self.latlng_to_pixel, zoom=zoom,is_round=False), raw_bounds)))
        #elif unit[0]=='pixel' and unit[1]=='latlng':
        #    raw_bounds = tuple(list(map(functools.partial(self.pixel_to_latlng, zoom=zoom), raw_bounds)))
        #else:
        #    raise ValueError('unit is "pixel" or "latlng" of 2 pieces list ex, ["latlng","pixel"]')

        x_min = raw_bounds[0][0]
        y_min = raw_bounds[0][1]
        x_max = raw_bounds[1][0]
        y_max = raw_bounds[1][1]

        center_point = ( (x_min+x_max)/2.0 , (y_min+y_max)/2.0 )

        width = [ x_max-x_min, y_max-y_min ]

        if not(minimum==() or minimum==[] or minimum==None):
            try:
                # correct mimimum bounds
                if width[0] < minimum[0]:
                    width[0] = minimum[0]
                if width[1] < minimum[1]:
                    width[1] = minimum[1]
            except:
                raise KeyError('minimum is (x_min, y_min) of tuple or list')
            
            x_min = center_point[0]-width[0]/2.0
            y_min = center_point[1]-width[1]/2.0
            x_max = center_point[0]+width[0]/2.0
            y_max = center_point[1]+width[1]/2.0
            
        if not(buff==() or buff==[] or buff==None):  
            x_min = x_min - buff[0]
            y_min = y_min - buff[1]
            x_max = x_max + buff[0]
            y_max = y_max + buff[1]
            
        bounds = np.array([[x_min, y_min], [x_max, y_max]])

        if form=='rectangle':
            # point order is counterclockwise.
            # [theta from x axis, np.array([4 points of spuare])]
            bounds = [0, np.array([[x_min,y_min],[x_max,y_min],[x_max,y_max],[x_min, y_max]]) ]

        return bounds
        
    @staticmethod
    def rotation_axis_matrix_2d(theta, is_affine=False):
        if is_affine:
            return np.array([[np.cos(theta),np.sin(theta),0],[-np.sin(theta),np.cos(theta),0], [0,0,1]])
        else:    
            return np.array([[np.cos(theta),np.sin(theta)],[-np.sin(theta),np.cos(theta)]])

    
    def terminal_node_aligned(self, polyline, minimum=[], buff=[], unit=['latlng','pixel'], zoom=18):
        """function to Minimum Bounding Rectangle aligned vector start to end.
        polyline (shapely.geometry.LineString) : LineString object. If default, use class instance.
        minimum (list of [x_min,y_min]) : Minimum width of Minimum Bounding Rectangle.
        If width < minimum, width=minimum and Rectangle is helf width from center point.
        
        minimum (list of [x_min,y_min]) : Minimum width of Minimum Bounding Rectangle.
        buff (list of [x_min, y_min]) : A rectangle buffer. Unit follows output unit.

        unit (list of str) [['latlng', 'pixel'], ['pixel', 'pixel'] ] : The first in the list shows the unit of input.
        THe second in the list shows the unit of output. And minimum unit follows the second in the list.
        
        If unit is ['latlng','pixel'], the inputed polyline unit is longtude and latitude, and return unit is pixel and minimum unit is pixel, 
        else if unit is latlng, return unit is longtude and latitude, and minimum unit is longtude and latitude.
        
        Warning, If unit is ['latlng','latlng'], later processing, convert 'latlng' to 'pixel', point of rectangle is a little shift, no more parallelograms.
        
        returns : [theta, np.array([[x_min,y_min],[x_max,y_min],[x_max,y_max],[x_min, y_max]]) ]
        Theta is angle[rad] vector start to end from x axis.
        """
        #if polyline=='self' and hasattr(self, 'polyline'):
        #    polyline = self.polyline
        #elif polyline=='self' and not hasattr(self, 'polyline'):
        #    raise KeyError('polyline is not found. Please input polyline or in class instance')
        
        if isinstance(polyline, str):
            polyline = shapely.wkt.loads(polyline)
            
        coords = np.array(polyline.coords)  # all LineString coordinate.

        coords = np.array(self.unit_change(coords, unit=unit,zoom=zoom, is_round=False))

        start_coord = coords[0]
        end_coord = coords[-1]
        # vector start to end
        vec_se = np.array([ end_coord[0]-start_coord[0], end_coord[1]-start_coord[1] ])
        # theta from x axis [rad]
        theta = np.arctan2( vec_se[1], vec_se[0] )

        rotation_axis_matrix = self.rotation_axis_matrix_2d(theta)

        # Coordinate transformation using rotation.
        coords_trans = np.dot(rotation_axis_matrix, coords.T).T


        # get_bounds
        bounds_trans = self.xy_aligned( LineString(coords_trans), minimum=minimum,\
                buff=buff, unit=['same','same'],form='rectangle', zoom=zoom)
        # reverse coordinate transformation
        rotation_axis_matrix_rev = self.rotation_axis_matrix_2d(-theta)
        bounds_ = np.dot(rotation_axis_matrix_rev, bounds_trans[1].T).T
        bounds = [theta, bounds_]
        
        return bounds
    
    
    @staticmethod
    def inpolygon(point, polygon):
        ''' 
        Judgment if point is included in polygon by Crossing Number Algorithm.
        point (list or tuple or np.array) : Coordinate to judge inside / outside. ex : [x,y],(x,y) , np.array([x,y])
        polygon (np.array, ndim=2) : Vertex coordinates of polygon. ex : np.array([[x1,y1], [x2,y2], [x3,y3], ...]).
        **end_point is not closing.**
        '''
        point_x = point[0]
        point_y = point[1]
        len_polygon = polygon.shape[0]
        if polygon.shape[1]!=2:
            raise KeyError('polygon is np.array([[x1,y1], [x2,y2], [x3,y3], ...])')
        x = polygon[:,0]
        y = polygon[:,1]
        
        inside = False
        for i1 in range(len_polygon): 
            i2 = (i1+1)%len_polygon
            if min(x[i1], x[i2]) < point_x < max(x[i1], x[i2]):
                #a = (y[i2]-y[i1])/(x[i2]-x[i1])
                #b = y[i1] - a*x[i1]
                #dy = a*point_x+b - point_y
                #if dy >= 0:
                if (y[i1] + (y[i2]-y[i1])/(x[i2]-x[i1])*(point_x-x[i1]) - point_y) > 0:
                    inside = not inside

        return inside    
    
    @staticmethod     
    def is_intersected_ls(a1, a2, b1, b2):
        """
        Judgment if line and line intersect.
        a1 (np.array) : one point of line a. ex. np.array([0,0])
        a2 (np.array) : another point of line a. ex. np.array([1,1])
        b1, b2(np.array) : points of line b.
        """
        EPS = 0.000001
        cross_b_and_a = np.cross(a2-a1, b1-a1) * np.cross(a2-a1, b2-a1)
        cross_a_and_b = np.cross(b2-b1, a1-b1) * np.cross(b2-b1, a2-b1)
        if cross_b_and_a<EPS and cross_a_and_b<EPS:
            return True
        else:
            return False

    @staticmethod
    def intersection_ls(a1, a2, b1, b2):
        """
        Find intersection of line and line .
        a1 (np.array) : one point of line a. ex. np.array([0,0])
        a2 (np.array) : another point of line a. ex. np.array([1,1])
        b1, b2(np.array) : points of line b.
        """
        b = b2-b1
        d1 = abs(np.cross(b, a1-b1))
        d2 = abs(np.cross(b, a2-b1))
        t = d1 / (d1 + d2)

        return a1 + (a2-a1) * t
    

    def _make_tile_mesh(self, pixel_bounds, TILE_SIZE, is_lines=False):

        # for make searching point, Make roughly tile points
        bounds_bounds = self.xy_aligned(Polygon(pixel_bounds), unit=['pixel','pixel'], form='minmax')
        min_x_s = (bounds_bounds[0,0] - TILE_SIZE[0]) // TILE_SIZE[0] * TILE_SIZE[0]
        min_y_s = (bounds_bounds[0,1] - TILE_SIZE[1]) // TILE_SIZE[1] * TILE_SIZE[1]
        max_x_s = (bounds_bounds[1,0] + TILE_SIZE[0]) // TILE_SIZE[0] * TILE_SIZE[0]
        max_y_s = (bounds_bounds[1,1] + TILE_SIZE[1]) // TILE_SIZE[1] * TILE_SIZE[1]

        # searching points range on pixel coordinate
        x_range = [ min_x_s, max_x_s, TILE_SIZE[0]]
        y_range = [ min_y_s, max_y_s, TILE_SIZE[1]]

        # Make coordinates of all searching points
        x_set = np.arange(x_range[0], x_range[1]+0.001, x_range[2]).reshape(-1,1)
        lx = x_set.shape[0]
        y_set = np.arange(y_range[0], y_range[1]+0.001, y_range[2])
        ly = y_set.shape[0]

        # Create xy pair
        points = np.empty((0,2),float)
        for y in y_set:
            y_ = np.tile(y, lx).reshape(-1,1)
            xy = np.concatenate([x_set, y_], axis=1)
            points = np.concatenate([points,xy], axis=0)
        len_points = lx*ly

        # linking tiles and points
        # tiles are represented by 4 points number
        # 6---7---8 
        # | 2'| 3'|
        # 3---4---5
        # | 0'| 1'|       
        # 0---1---2
        # 0,1,2 : points number, 0',1',2' : tiles number
        # this case, tiles 0' is [0, 1, 4, 3]

        lx1 = lx-1
        ly1 = ly-1
        tiles = []
        tiles_append = tiles.append
        for j in range(ly1):
            for i in range(lx1):
                tiles_append([i +j+lx1*j, i+1 +j+lx1*j, i+2+lx1 +j+lx1*j, i+1+lx1 +j+lx1*j])
        len_tiles = len(tiles)
        tiles = np.array(tiles)
        
        if is_lines:
            # linking tiles and lines, lines and points
            lines = []  # all line segments composed of points
            lines_append = lines.append
            owner = []  # Which tile the lines belong to
            owner_append = owner.append
            for j in range(ly):
                for i in range(lx1):
                    lines_append([i +j+lx1*j, i+1 +j+lx1*j])
                    if j==0:
                        owner_append([i +lx1*j])
                    elif j==ly-1:
                        owner_append([i-lx1 + lx1*j])
                    else:
                        owner_append([i-lx1 + lx1*j, i +lx1*j])
                        
            for j in range(ly1):
                for i in range(lx):
                    lines_append([i +j+lx1*j, i+1+lx1 +j+lx1*j])
                    if i==0:
                        owner_append([i +lx1*j])
                    elif i==lx-1:
                        owner_append([i-1 + lx1*j])
                    else:
                        owner_append([i-1 + lx1*j, i +lx1*j])

            len_lines = len(lines)
            lines = np.array(lines)
            return points, len_points, tiles, len_tiles, lines, len_lines, owner
        else:
            return points, len_points, tiles, len_tiles
        
        
    def overlappingTiles(self, bounds, unit=['pixel','pixel'], zoom='self', TILE_SIZE='self'):
        """
        bounds (list) : input [theta, np.array([[x_min,y_min],[x_max,y_min],[x_max,y_max],[x_min, y_max]])] by xy_aligned or terminal node aligned.
        zoom (int)[0-18] : zoom level.
        
        unit (list of str) [['latlng', 'pixel'], ['pixel', 'pixel'] ] : The first in the list shows the unit of input.
        THe second in the list shows the unit of output. And minimum unit follows the second in the list.
        If unit is ['latlng','pixel'], the inputed polyline unit is longtude and latitude, and return unit is pixel and minimum unit is pixel, 
        else if unit is latlng, return unit is longtude and latitude, and minimum unit is longtude and latitude.

        returns : return pickup_tiles as np.array([[x1, y1], [x2, y2],...])
        """

        if zoom=='self' and hasattr(self, 'zoom'):
            zoom = self.zoom
        elif zoom=='self' and not hasattr(self, 'zoom'):
            raise KeyError('zoom is not found. Please input zoom or in class instance')

        if TILE_SIZE=='self' and hasattr(self, 'TILE_SIZE'):
            TILE_SIZE = self.TILE_SIZE
        elif TILE_SIZE=='self' and not hasattr(self, 'TILE_SIZE'):
            raise KeyError('TILE_SIZE is not found. Please input TILE_SIZE or in class instance')


        if len(bounds)==4:  # if bounds=(x_min,ymin,x_max,y_max)
            bounds = [0, np.array([[bounds[0],bounds[1]],[bounds[2],bounds[1]],[bounds[2],bounds[3]],[bounds[0], bounds[3]]]) ]

        theta = bounds[0]

        # probably, bounds is pixel, from here bounds must be pixel unit.
        bounds_pixel = np.array(self.unit_change(bounds[1], unit=unit,zoom=zoom, is_round=False))

        points, len_points, tiles, len_tiles = self._make_tile_mesh(bounds_pixel, TILE_SIZE, is_lines=False)

        # judgement points are whether in bounds.
        points_is_in_bounds = np.array(list(map(functools.partial(self.inpolygon, polygon=bounds_pixel), points)))

        # tiles have how many points in bounds.
        howmany_points_in_bounds = []
        howmany_points_in_bounds_append = howmany_points_in_bounds.append
        for i in range(len_tiles):
            howmuch_in_bounds = points_is_in_bounds[tiles[i]].sum()
            howmany_points_in_bounds_append(howmuch_in_bounds)

        # pick up tiles having at least 1 points in bounds.
        is_in_bounds = [hpib !=0 for hpib in howmany_points_in_bounds]


        # ---------Tile having bounds corner contains, because the case is exists that 
        # tile all points is not in bounds, but bounds corner points is in the tile.--------

        # tile_base_point
        tile_base_points = []
        tile_base_points_append = tile_base_points.append
        for tile_num in range(len_tiles):
            tile_base_points_append(points[tiles[tile_num][0]])
        tile_base_points = np.array(tile_base_points)

        # Calculate which position of which tile is relative to the 4 points of Bounds.
        len_bounds_pixel = len(bounds_pixel)

        bounds_corner_tiles_index = []
        for i in range(len_bounds_pixel):  # i=0,1,2,3 if rectangle
            corner_jugdment = -(tile_base_points - bounds_pixel[i])
            tile_corner_index = np.where(np.all((0.0 <= corner_jugdment) * (corner_jugdment[:,[0]] < TILE_SIZE[0]) * (corner_jugdment[:,[1]] < TILE_SIZE[1]), axis=1) )
            bounds_corner_tiles_index.append(tile_corner_index)
            
        bounds_corner_tiles_index = np.array(bounds_corner_tiles_index).reshape(-1,)

        for index in bounds_corner_tiles_index:
            is_in_bounds[index] = True  
        # -------------------------------------------------------

        pickup_tiles = points[tiles[is_in_bounds,0]] / TILE_SIZE
        pickup_tiles = pickup_tiles.astype(int)

        return pickup_tiles

    def overlappingTileSegments(self, bounds, unit=['pixel','pixel'], zoom='self', TILE_SIZE='self'):
        """
        bounds (list) : input [theta, np.array([[x_min,y_min],[x_max,y_min],[x_max,y_max],[x_min, y_max]])] by xy_aligned or terminal node aligned.
        zoom (int)[0-18] : zoom level.

        returns : return pickup_tiles, pickup_tiles_intersection as np.array([[x1, y1], [x2, y2],...]), 
        np.array([[x11,y11],[x12,y12],[x13,y13]], ...). x11, y11 and x12, y12 is intersections of bounds lines and tiles lines.
        x13, y13 is bounds corner points in the tiles. If intersections or corner points are not exist, it is in np.nan.
        """
        
        if zoom=='self' and hasattr(self, 'zoom'):
            zoom = self.zoom
        elif zoom=='self' and not hasattr(self, 'zoom'):
            raise KeyError('zoom is not found. Please input zoom or in class instance')
        
        if TILE_SIZE=='self' and hasattr(self, 'TILE_SIZE'):
            TILE_SIZE = self.TILE_SIZE
        elif TILE_SIZE=='self' and not hasattr(self, 'TILE_SIZE'):
            raise KeyError('TILE_SIZE is not found. Please input TILE_SIZE or in class instance')


        if len(bounds)==4:  # if bounds=(x_min,ymin,x_max,y_max)
            bounds = [0, np.array([[bounds[0],bounds[1]],[bounds[2],bounds[1]],[bounds[2],bounds[3]],[bounds[0], bounds[3]]]) ]

        theta = bounds[0]

        # warning :: pixel coordinate is y axis inversion.
        # probably, bounds is pixel, from here bounds must be pixel unit.
        bounds_pixel = np.array(self.unit_change(bounds[1], unit=unit,zoom=zoom, is_round=False))

        points, len_points, tiles, len_tiles, lines, len_lines, owner = self._make_tile_mesh(bounds_pixel, TILE_SIZE, is_lines=True)


        # judgement points are whether in bounds.
        points_is_in_bounds = np.array(list(map(functools.partial(self.inpolygon, polygon=bounds_pixel), points)))

        # intersects with bounds when the end point of the line is True and False
        line_points_in_bounds = []
        line_points_in_bounds_append = line_points_in_bounds.append
        for i in range(len_lines):
            howmany_in_bounds = points_is_in_bounds[lines[i]].sum()
            line_points_in_bounds_append(howmany_in_bounds)

        # lines having cross==True points and False points, line is cross to bounds.
        cross_lines = [lpib==1 for lpib in line_points_in_bounds]



        # Judgment which bounds the intersecting line intersects
        cross_lines_coords = points[lines[cross_lines]]
        len_cross_lines_coords = len(cross_lines_coords)

        # pixel_bounds having 4 lines, its represent points.
        len_pixel_bounds = len(bounds_pixel)
        pb_lines_coords = []
        pb_lines_coords_append = pb_lines_coords.append
        for i in range(len_pixel_bounds):
            if i!=len_pixel_bounds-1:
                pb_lines_coords_append([bounds_pixel[i],bounds_pixel[i+1]])
            elif i==len_pixel_bounds-1:
                pb_lines_coords_append([bounds_pixel[i],bounds_pixel[0]])

        # judgment lines cross which bounds lines.
        which_lines_cross = []
        which_lines_cross_append = which_lines_cross.append
        for j in range(len_cross_lines_coords):
            for i in range(len_pixel_bounds):
                is_lines_cross = self.is_intersected_ls(pb_lines_coords[i][0], pb_lines_coords[i][1], cross_lines_coords[j][0], cross_lines_coords[j][1])
                if is_lines_cross:
                    which_lines_cross_append(i)
                    break
                elif (not is_lines_cross) and i==len_pixel_bounds-1:
                    which_lines_cross_append(np.nan)
                
                
        # Find intersection
        intersection = []
        intersection_append = intersection.append
        for j in range(len_cross_lines_coords):
            i = which_lines_cross[j]
            intersec = self.intersection_ls(pb_lines_coords[i][0], pb_lines_coords[i][1], cross_lines_coords[j][0], cross_lines_coords[j][1])
            intersection_append(intersec)
            
        intersection = np.array(intersection)

        # tile number having cross lines.
        cross_owner = []
        cross_owner_append = cross_owner.append
        for own, is_cross in zip(owner, cross_lines):
            if is_cross:
                cross_owner_append(own)

        # The coordinates of the intersection of tiles
        tiles_intersection = [[] for i in range(len_tiles)]
        for cross_line_num, cro_own in enumerate(cross_owner):
            for tile_num in cro_own:
                tiles_intersection[tile_num].append(intersection[cross_line_num])

        # to calculate conveniently, convert numpy.array      
        tiles_intersection = [ [[np.nan,np.nan],[np.nan,np.nan]] if ti==[] else ti for ti in tiles_intersection]
        tiles_intersection = np.array(tiles_intersection)


        # tile_base_point
        tile_base_points = []
        tile_base_points_append = tile_base_points.append
        for tile_num in range(len_tiles):
            tile_base_points_append(points[tiles[tile_num][0]])
        tile_base_points = np.array(tile_base_points)

        # Convert to coordinates in tile
        for tile_num in range(len_tiles):
            if np.isnan(tiles_intersection[tile_num]).all():
                continue
            tile_base_point = tile_base_points[tile_num]
            
            for i in range(len(tile_base_point)):  # 2d:i=0,1
                tiles_intersection[tile_num][:,i] -= tile_base_point[i]


        # Calculate which position of which tile is relative to the 4 points of Bounds.
        bounds_corner_tiles_index = []
        bounds_corner_tile_coords = []
        for i in range(len_pixel_bounds):  # i=0,1,2,3 if rectangle
            corner_jugdment = -(tile_base_points - bounds_pixel[i])
            tile_corner_index = np.where(np.all((0.0 <= corner_jugdment) * (corner_jugdment[:,[0]] < TILE_SIZE[0]) * (corner_jugdment[:,[1]] < TILE_SIZE[1]), axis=1) )
            bounds_corner_tiles_index.append(tile_corner_index)
            bounds_corner_tile_coords.append(corner_jugdment[tile_corner_index])
            
        bounds_corner_tiles_index = np.array(bounds_corner_tiles_index).reshape(-1,)
        bounds_corner_tile_coords = np.array(bounds_corner_tile_coords).reshape(-1,2)

        # Add nan to the coordinates of the third point for the time being
        tiles_intersection = np.concatenate([tiles_intersection, np.full( (len_tiles,1,2) ,np.nan)], axis=1)

        for i in range(len(bounds_corner_tile_coords)):
            bounds_tile_num = bounds_corner_tiles_index[i]
            tiles_intersection[bounds_tile_num][2] = bounds_corner_tile_coords[i]

        # check
        #for i in range(len_pixel_bounds):  # i=0,1,2,3 if rectangle
        #    if not self.inpolygon(pixel_bounds[i] , points[tiles[bounds_corner_tiles[i]]]):
        #        raise ValueError

        # tiles have how many points in bounds.
        howmany_points_in_bounds = []
        howmany_points_in_bounds_append = howmany_points_in_bounds.append
        for i in range(len_tiles):
            howmuch_in_bounds = points_is_in_bounds[tiles[i]].sum()
            howmany_points_in_bounds_append(howmuch_in_bounds)

        # pick up tiles having at least 1 points in bounds.
        is_in_bounds = [hpib !=0 for hpib in howmany_points_in_bounds]

        # Tile having bounds corner contains, because the case is exists that 
        # tile all points is not in bounds, but bounds corner points is in the tile.
        for index in bounds_corner_tiles_index:
            is_in_bounds[index] = True
            

        pickup_tiles = points[tiles[is_in_bounds,0]] / TILE_SIZE
        pickup_tiles = pickup_tiles.astype(int)

        pickup_tiles_intersection = tiles_intersection[is_in_bounds]

        return pickup_tiles, pickup_tiles_intersection
    

    def _pickup_file_search(self, pickup_tiles, zoom, file_path, file_extention):
        if not file_path[-1:]=='/':
            file_path = file_path+'/'
        file_path = file_path + str(zoom) + '/'
            
        pickup_tiles_list = []
        for pit in pickup_tiles:
            x = pit[0]
            y = pit[1]
            path = file_path +str(x) + '/'+str(y) + file_extention
            pickup_tiles_list.append(path)
            
        # all database tiles.
        tilesfile_list = glob.glob(file_path+'*/*')
        isnot_exist_files = set(pickup_tiles_list) - set(tilesfile_list)

        # if pickup_file is not exist, raise error
        if not isnot_exist_files==set():
            raise ValueError(str(isnot_exist_files)+' is not exist')
        return pickup_tiles_list
    
    # 黒下地に足していくのとくっつけるのが、うまく一つのライブラリで実現できずに、cv2とPillowを両方使ってしまった。
    
    def _concat_h_blank(self, im1, im2, color=(0,0,0)):
        dst = Image.new('RGB', (im1.width + im2.width, max(im1.height, im2.height)), color)
        dst.paste(im1, (0, 0))
        dst.paste(im2, (im1.width, 0))
        return dst

    def _concat_v_blank(self, im1, im2, color=(0,0,0)):
        dst = Image.new('RGB', (max(im1.width, im2.width), im1.height + im2.height), color)
        dst.paste(im1, (0, 0))
        dst.paste(im2, (0, im1.height))
        return dst

    def _concat_h_multi_blank(self, im_list, color=(0,0,0)):
        _im = im_list.pop(0)
        for im in im_list:
            _im = self._concat_h_blank(_im, im, color)
        return _im

    def _concat_v_multi_blank(self, im_list, color=(0,0,0)):
        _im = im_list.pop(0)
        for im in im_list:
            _im = self._concat_v_blank(_im, im, color)
        return _im

    def _concat_tile_blank(self, im_list_2d, color=(0,0,0)):
        im_list_v = [self._concat_h_multi_blank(im_list_h, color) for im_list_h in im_list_2d]
        return self._concat_v_multi_blank(im_list_v, color)

    def _make_dummy(self, im, color=(0,0,0)):
        dst = Image.new('RGB', (im.width, im.height), color)
        return dst

    def _pil2cv(self, image):
        ''' PIL型 -> OpenCV型 '''
        new_image = np.array(image, dtype=np.uint8)
        if new_image.ndim == 2:  # モノクロ
            pass
        elif new_image.shape[2] == 3:  # カラー
            new_image = cv2.cvtColor(new_image, cv2.COLOR_RGB2BGR)
        elif new_image.shape[2] == 4:  # 透過
            new_image = cv2.cvtColor(new_image, cv2.COLOR_RGBA2BGRA)
        return new_image

    def _cv2pil(self, image):
        ''' OpenCV型 -> PIL型 '''
        new_image = image.copy()
        if new_image.ndim == 2:  # モノクロ
            pass
        elif new_image.shape[2] == 3:  # カラー
            new_image = cv2.cvtColor(new_image, cv2.COLOR_BGR2RGB)
        elif new_image.shape[2] == 4:  # 透過
            new_image = cv2.cvtColor(new_image, cv2.COLOR_BGRA2RGBA)
        new_image = Image.fromarray(new_image)
        return new_image
    
    
    def polygon_crop_cv(self, img, polygon, mode='all'):
        """
        The function to crop.
        mode (list of str) 'croped','mask','dst','dst2' : If 'all' 4 all pattern images return.
        dst : black back crop, dst2 : white back crop.
        """
        if mode=='all':
            mode=['croped', 'mask', 'dst', 'dst2']
        elif mode!='all' and isinstance(mode,str):
            mode = [mode]
        
        returns = []
        rect = cv2.boundingRect(polygon)
        x,y,w,h = rect
        croped = img[y:y+h, x:x+w].copy()
        if 'croped' in mode:
            ## (1) Crop the bounding rect
            returns.append(croped)
        
        polygon = polygon - polygon.min(axis=0)
        mask = np.zeros(croped.shape[:2], np.uint8)  
        if 'mask' in mode:
            ## (2) make mask
            cv2.drawContours(mask, [polygon], -1, (255, 255, 255), -1, cv2.LINE_AA)
            returns.append(mask)
        
        if 'dst' in mode:
            ## (3) do bit-op
            dst = cv2.bitwise_and(croped, croped, mask=mask)
            returns.append(dst)
            
        if 'dst2' in mode:
            ## (4) add the white background
            bg = np.ones_like(croped, np.uint8)*255
            cv2.bitwise_not(bg,bg, mask=mask)
            dst2 = bg+ dst
            returns.append(dst2)
        return returns


    def concat_tile(self, bounds, pickup_tiles, file_path, 
                           file_extention='.webp', save_path='./',
                           draw_polyline=False, draw_bounds=True, crop_mode='dst', 
                           rotate=False, return_check=False,
                           zoom='self', TILE_SIZE='self'):
        """
        A function that collects tiles in bounds and connects the top of 
        the satellite image with the polyline.
        bounds (list) : returns for xy_aligned or terminal_node_aligned.
        pickup_tiles (list) : returns for overlappingTile function.

        file_path (str) : path for where there are satellite image tiles. ex. '../datasets/'
        file_extention (str) : Extension for tile image files. Probably, '.webp'.
        save_file_path (str) : path for save image file.

        draw_polyline (False or shapely.geometry.LineString) : polyline using make bounds.) If False, polyline is not drawn.
        draw_bounds (bool) : If True, bounds is drawn.
        crop_mode (list of str) 'croped','mask','dst','dst2' or False: If 'all' 4 all pattern images return.
        dst, black back crop, dst2, white back crop.
        if False, no croped.

        rotate (str or float or False)['theta','nearest', 'vertical', 'horizontal'] : If float, cropped image rotate input angle[rad].
        If theta, rotate Angle between start point and end point of polyline,  if nearest, rotate along nearest x or y axis,
        if vertical, rotate along the nearest x axis, as well, horizontal y axis.

        ### Warning ; Pixel coordinate is Y-axis flip. 
        The image you see has the coordinates without y-axis flipping, 
        but the numbers themselves are in the y-axis flipping coordinate system.
        In short, the angle is in the reverse rotation direction as usual.

        return_check (bool) : If True, return Pillow image to check.

        zoom (int)[0-18] : zoom level.
        TILE_SIZE (tuple of int) : The tile size(px). Probably, (256, 256).
        """
        if zoom=='self' and hasattr(self, 'zoom'):
            zoom = self.zoom
        elif zoom=='self' and not hasattr(self, 'zoom'):
            raise KeyError('zoom is not found. Please input zoom or in class instance')

        if TILE_SIZE=='self' and hasattr(self, 'TILE_SIZE'):
            TILE_SIZE = self.TILE_SIZE
        elif TILE_SIZE=='self' and not hasattr(self, 'TILE_SIZE'):
            raise KeyError('TILE_SIZE is not found. Please input TILE_SIZE or in class instance')

        # the last of file_path '/' may or may not be.
        pickup_tiles_list = self._pickup_file_search(pickup_tiles, zoom, file_path, file_extention)

        # concat image
        img_list = [Image.open(pickup_tile) for pickup_tile in pickup_tiles_list]
        dummy = self._make_dummy(img_list[0])

        min_x = pickup_tiles[:,0].min()
        min_y = pickup_tiles[:,1].min()
        max_x = pickup_tiles[:,0].max()
        max_y = pickup_tiles[:,1].max()

        width_x = max_x - min_x
        width_y = max_y - min_y

        pt_standard = pickup_tiles.copy()
        pt_standard[:,0] -= min_x
        pt_standard[:,1] -= min_y

        arrangement_image = [[dummy for i in range(width_x+1)] for j in range(width_y+1)]

        len_pickup_tiles = len(pickup_tiles)
        for i in range(len_pickup_tiles):
            arrangement_image[pt_standard[i,1]][pt_standard[i,0]] = img_list[i]

        concated_image = self._concat_tile_blank(arrangement_image)

        polyline_image = concated_image.copy()

        # draw polyline
        if type(draw_polyline)==str:
            draw_polyline = shapely.wkt.loads(draw_polyline)
            
        if type(draw_polyline)==shapely.geometry.linestring.LineString:
            polyline = draw_polyline
            polyline_coords = np.array(polyline.coords)
            pixel_coords = np.array(list(map(functools.partial(self.latlng_to_pixel, zoom=zoom,is_round=False), polyline_coords)))

            # change tile coordinate to pixel coordinate, from min point is (0,0).
            pixel_coords[:,0] -= min_x * TILE_SIZE[0]
            pixel_coords[:,1] -= min_y * TILE_SIZE[1]
            pixel_coords_tuple = tuple(map(tuple, pixel_coords))

            draw = ImageDraw.Draw(polyline_image)
            draw.line(pixel_coords_tuple, fill=(255, 255, 0), width=10)
        elif draw_polyline==True:
            raise ValueError('draw_polyline is False or shapely.geometry.linestring.LineString')


        # draw bounds
        bounds_pixel = bounds[1].copy()
        # change tile coordinate to pixel coordinate, from min point is (0,0).
        bounds_pixel[:,0] -= min_x * TILE_SIZE[0]
        bounds_pixel[:,1] -= min_y * TILE_SIZE[1]

        if draw_bounds:
            bounds_pixel_drow = np.concatenate([bounds_pixel, bounds_pixel[[0]]], axis=0)
            bounds_pixel_tuple = tuple(map(tuple, bounds_pixel_drow))

            draw = ImageDraw.Draw(polyline_image)
            draw.line(bounds_pixel_tuple, fill=(255, 0, 255), width=10)



        # rotate image
        polyline_theta = bounds[0]

        if isinstance(rotate, float) or isinstance(rotate,int):
            theta = rotate
            
        elif isinstance(rotate, str):
            if rotate=='theta':
                theta=polyline_theta
                
            elif rotate=='nearest':
                # nearest
                xy_axis = np.arange(-2*np.pi, 2*np.pi+0.0001, np.pi/2)
                nearest_axis_index = np.argmin(abs(xy_axis - polyline_theta))

                nearest_axis = xy_axis[nearest_axis_index]
                theta = polyline_theta - nearest_axis
                
            elif rotate=='horizontal':
                # horizontal
                x_axis = np.arange(-2*np.pi, 2*np.pi+0.0001, np.pi)
                horizontal_axis_index = np.argmin(abs(x_axis - polyline_theta))

                horizontal_axis = x_axis[horizontal_axis_index]
                theta = polyline_theta - horizontal_axis
                
            elif rotate=='vertical':
                # vertical
                y_axis = np.arange(-3/2*np.pi, 3/2*np.pi+0.0001, np.pi)
                vertical_axis_index = np.argmin(abs(y_axis - polyline_theta))

                vertical_axis = y_axis[vertical_axis_index]
                theta = polyline_theta - vertical_axis
                
            else:
                raise ValueError('rotate is one of the fllowing, False, float, "theta", "nearest", "vertical", "horizontal"')
            
        elif rotate==False or rotate==None or polyline_theta==0:  # Do not rotate
            pass  
        else:
            raise ValueError('rotate is one of the fllowing, False, float, "theta", "nearest", "vertical", "horizontal"')


        if not rotate==False or rotate==None or polyline_theta==0:
            # Rotate image
            polyline_image_rotate = polyline_image.rotate(theta*180/np.pi, expand=True)

            center_point = np.array(polyline_image.size) / 2
            x_c = center_point[0]
            y_c = center_point[1]

            # Use affine transformation, so increase dimension by one.
            dummy_point = np.ones((bounds_pixel.shape[0], 1))

            # Move in parallel to the coordinates with the center as the origin
            bounds_affine = np.concatenate([bounds_pixel, dummy_point], axis=1)
            translation_matrix = np.array([[1,0,-x_c], [0,1,-y_c], [0,0,1]])

            bounds_trans = np.dot(translation_matrix, bounds_affine.T)

            # Rotate from center
            rotation_axis_matrix = self.rotation_axis_matrix_2d(theta, is_affine=True)
            bounds_trans_rotate = np.dot(rotation_axis_matrix, bounds_trans)

            # Move the lower left to the origin again
            after_center_point = np.array(polyline_image_rotate.size) / 2

            x_ca = after_center_point[0]
            y_ca = after_center_point[1]
            after_translation_matrix = np.array([[1,0,x_ca],[0,1,y_ca],[0,0,1]])

            bounds_after = np.dot(after_translation_matrix, bounds_trans_rotate).T
            bounds_after_2d = np.delete(bounds_after,-1,1)

            # use image
            use_image  = polyline_image_rotate
            use_bounds = bounds_after_2d

        else:
            use_image  = polyline_image
            use_bounds = bounds_pixel


        image_cv = self._pil2cv(use_image)

        # bounds is rounded to croped.
        # That is because, croped bound must be rounded bound. But drawn bounds is not rounded.
        use_bounds = use_bounds.round()
        use_bounds = use_bounds.astype(int)


        croped, mask, dst, dst2 = self.polygon_crop_cv(image_cv, use_bounds, mode='all')

        if crop_mode=='all':
            crop_mode=['croped', 'mask', 'dst', 'dst2']
        elif crop_mode!='all' and isinstance(crop_mode,str):
            crop_mode = [crop_mode]
            
        if crop_mode==False or crop_mode==None or crop_mode==[]:
            cv2.imwrite(save_path+'nocroped.png', image_cv)

        else:        
            if 'croped' in crop_mode:
                ## (1) Crop the bounding rect
                cv2.imwrite(save_path+'croped.png', croped)
            if 'mask' in crop_mode:
                ## (2) make mask
                cv2.imwrite(save_path+'mask.png', mask)
            if 'dst' in crop_mode:
                ## (3) do bit-op
                cv2.imwrite(save_path+'dst.png', dst)
            if 'dst2' in crop_mode:
                ## (4) add the white background
                cv2.imwrite(save_path+'dst2.png', dst2)

        # for check, return is exist.
        if return_check:
            return use_image

    def _to_convex_rectangle(self, rectangle):
        """
        Rectangle fixs to convex rectangle. In other words, rearrange the four points of the quadrangle so that they do not intersect.
        rectangle (2d np.ndarray) : 4 point of np.ndarray. ex. np.array([[0,0],[1,0],[0,1],[1,1]])
        return : Rearranged 4 point of np.ndarray. ex. np.array([[0,0],[1,0],[1,1],[0,1]])
        """
        is_01_23_cross = self.is_intersected_ls(rectangle[0], rectangle[1],
                                            rectangle[2], rectangle[3])

        is_02_13_cross = self.is_intersected_ls(rectangle[0], rectangle[2],
                                            rectangle[1], rectangle[3])

        is_03_12_cross = self.is_intersected_ls(rectangle[0], rectangle[3],
                                            rectangle[1], rectangle[2])

        if is_01_23_cross:
            convex_rectangle = np.array([rectangle[0], rectangle[2], rectangle[1], rectangle[3]])
        elif is_02_13_cross:
            convex_rectangle = np.array([rectangle[0], rectangle[1], rectangle[2], rectangle[3]])
        elif is_03_12_cross:
            convex_rectangle = np.array([rectangle[0], rectangle[1], rectangle[3], rectangle[2]])
        else:
            raise ValueError('this is not rectangle')
        
        return convex_rectangle



    def concat_tile_segment(self, pickup_tiles, pickup_tiles_intersection, file_path, 
                           file_extention='.webp', save_path='./',
                           draw_polyline=False, draw_bounds=True,
                            rotate=False, return_check=False,
                            crop_mode='dst', zoom='self', TILE_SIZE='self'):
        """
        A function that collects tiles in bounds and connects the top of 
        the satellite image with the polyline.
        polyline (shapely.geometry.LineString) : polyline using make bounds.
        pickup_tiles (list) : returns for overlappingTile function.
        pickup_tiles_intersection (list) : returns for overlappingTileSegment function.


        file_path (str) : path for where there are satellite image tiles. ex. '../datasets/'
        file_extention (str) : Extension for tile image files. Probably, '.webp'.
        save_file_path (str) : path for save image file.

        is_polyline (bool) : If True, polyline is drawn.
        is_bounds (bool) : If True, bounds is drawn.
        crop_mode (list of str) 'croped','mask','dst','dst2' or False: If 'all' 4 all pattern images return.
        dst, black back crop, dst2, white back crop.
        if False, no croped.

        rotate (str or float or False)['theta','nearest', 'vertical', 'horizontal'] : If float, cropped image rotate input angle[rad].
        If theta, rotate Angle between start point and end point of polyline,  if nearest, rotate along nearest x or y axis,
        if vertical, rotate along the nearest x axis, as well, horizontal y axis.

        ### Warning ; Pixel coordinate is Y-axis flip. 
        The image you see has the coordinates without y-axis flipping, 
        but the numbers themselves are in the y-axis flipping coordinate system.
        In short, the angle is in the reverse rotation direction as usual.

        return_check (bool) : If True, return Pillow image to check.

        zoom (int)[0-18] : zoom level.
        TILE_SIZE (tuple of int) : The tile size(px). Probably, (256, 256).
        """
                
        if zoom=='self' and hasattr(self, 'zoom'):
            zoom = self.zoom
        elif zoom=='self' and not hasattr(self, 'zoom'):
            raise KeyError('zoom is not found. Please input zoom or in class instance')

        if TILE_SIZE=='self' and hasattr(self, 'TILE_SIZE'):
            TILE_SIZE = self.TILE_SIZE
        elif TILE_SIZE=='self' and not hasattr(self, 'TILE_SIZE'):
            raise KeyError('TILE_SIZE is not found. Please input TILE_SIZE or in class instance')

        # the last of file_path '/' may or may not be.
        pickup_tiles_list = self._pickup_file_search(pickup_tiles, zoom, file_path, file_extention)

        # concat image
        img_list = [Image.open(pickup_tile) for pickup_tile in pickup_tiles_list]
        dummy = self._make_dummy(img_list[0])

        min_x = pickup_tiles[:,0].min()
        min_y = pickup_tiles[:,1].min()
        max_x = pickup_tiles[:,0].max()
        max_y = pickup_tiles[:,1].max()

        width_x = max_x - min_x
        width_y = max_y - min_y

        pt_standard = pickup_tiles.copy()
        pt_standard[:,0] -= min_x
        pt_standard[:,1] -= min_y

        arrangement_image = [[dummy for i in range(width_x+1)] for j in range(width_y+1)]

        len_pickup_tiles = len(pickup_tiles)
        for i in range(len_pickup_tiles):
            arrangement_image[pt_standard[i,1]][pt_standard[i,0]] = img_list[i]

        concated_image = self._concat_tile_blank(arrangement_image)

        polyline_image = concated_image.copy()

        # draw polyline
        if type(draw_polyline)==str:
            draw_polyline = shapely.wkt.loads(draw_polyline)
            
        if type(draw_polyline)==shapely.geometry.linestring.LineString:
            polyline = draw_polyline
            polyline_coords = np.array(polyline.coords)
            pixel_coords = np.array(list(map(functools.partial(self.latlng_to_pixel, zoom=zoom,is_round=False), polyline_coords)))

            # change tile coordinate to pixel coordinate, from min point is (0,0).
            pixel_coords[:,0] -= min_x * TILE_SIZE[0]
            pixel_coords[:,1] -= min_y * TILE_SIZE[1]
            pixel_coords_tuple = tuple(map(tuple, pixel_coords))

            draw = ImageDraw.Draw(polyline_image)
            draw.line(pixel_coords_tuple, fill=(255, 255, 0), width=10)
        elif draw_polyline==True:
            raise ValueError('draw_polyline is False or shapely.geometry.linestring.LineString')




        # This function is same to concat_tile function except here.
        # It may be necessary to change the common part to another function, but leave it alone.
        # -----------------------------------------------------------------------------------------
        # draw bounds 
        is_bound_tile = np.all(~np.isnan(pickup_tiles_intersection[:,2]), axis=1)

        bounds_tile_num = np.where(is_bound_tile)[0]
        bounds_position = pickup_tiles_intersection[is_bound_tile][:,2]

        len_bounds = len(bounds_tile_num)  # probably 4

        bounds_pixel = []
        for i in range(len_bounds):
            bound = pt_standard[bounds_tile_num[i]] * TILE_SIZE + bounds_position[i]
            bounds_pixel.append(bound)
            
        bounds_pixel = np.array(bounds_pixel)
        bounds_pixel = self._to_convex_rectangle(bounds_pixel)
        
        
        if draw_bounds:
            bounds_pixel_drow = np.concatenate([bounds_pixel, bounds_pixel[[0]]], axis=0)
            bounds_pixel_tuple = tuple(map(tuple, bounds_pixel_drow))

            draw = ImageDraw.Draw(polyline_image)
            draw.line(bounds_pixel_tuple, fill=(255, 0, 255), width=10)        

        # rotate image
        # polyline angle is not exist, because of bounds is not input, make polyline angle.
        if type(draw_polyline)==shapely.geometry.linestring.LineString:
            coords = np.array(polyline.coords)  # all LineString coordinate.
            coords = np.array(self.unit_change(coords, unit=['latlng','pixel'],zoom=zoom, is_round=False))
            start_coord = coords[0]
            end_coord = coords[-1]

        else:
            
            long_boundary = np.argmax([np.linalg.norm(bounds_pixel[0]-bounds_pixel[1]),np.linalg.norm(bounds_pixel[0]-bounds_pixel[-1])])
            # from bounds, make some angle.
            if long_boundary==0: 
                start_coord = bounds_pixel[0]
                end_coord = bounds_pixel[1]
            elif long_boundary==1:
                start_coord = bounds_pixel[0]
                end_coord = bounds_pixel[-1]
            else:
                start_coord = bounds_pixel[0]
                end_coord = bounds_pixel[1]   


        # vector start to end
        vec_se = np.array([ end_coord[0]-start_coord[0], end_coord[1]-start_coord[1] ])
        # theta from x axis [rad]
        polyline_theta = np.arctan2( vec_se[1], vec_se[0] )

        #%%

        if isinstance(rotate, float) or isinstance(rotate,int):
            theta = rotate
            
        elif isinstance(rotate, str):
            if rotate=='theta':
                if type(draw_polyline)==shapely.geometry.linestring.LineString:
                    theta=polyline_theta
                else:
                    raise ValueError('rotate="theta" is only use type(draw_polyline)=shapely.geometry.linestring.LineString')
                
            elif rotate=='nearest':
                # nearest
                xy_axis = np.arange(-2*np.pi, 2*np.pi+0.0001, np.pi/2)
                nearest_axis_index = np.argmin(abs(xy_axis - polyline_theta))

                nearest_axis = xy_axis[nearest_axis_index]
                theta = polyline_theta - nearest_axis
                
            elif rotate=='horizontal':
                # horizontal
                x_axis = np.arange(-2*np.pi, 2*np.pi+0.0001, np.pi)
                horizontal_axis_index = np.argmin(abs(x_axis - polyline_theta))

                horizontal_axis = x_axis[horizontal_axis_index]
                theta = polyline_theta - horizontal_axis
                
            elif rotate=='vertical':
                # vertical
                y_axis = np.arange(-3/2*np.pi, 3/2*np.pi+0.0001, np.pi)
                vertical_axis_index = np.argmin(abs(y_axis - polyline_theta))

                vertical_axis = y_axis[vertical_axis_index]
                theta = polyline_theta - vertical_axis
                
            else:
                raise ValueError('rotate is one of the fllowing, False, float, "theta", "nearest", "vertical", "horizontal"')
            
        elif rotate==False or rotate==None or polyline_theta==0:  # Do not rotate
            pass  
        else:
            raise ValueError('rotate is one of the fllowing, False, float, "theta", "nearest", "vertical", "horizontal"')

        # ------------------------------------------------------------------------------
        # This function is same to concat_tile function except here.
        # It may be necessary to change the common part to another function, but leave it alone.



        if not rotate==False or rotate==None or polyline_theta==0:
            # Rotate image
            polyline_image_rotate = polyline_image.rotate(theta*180/np.pi, expand=True)

            center_point = np.array(polyline_image.size) / 2
            x_c = center_point[0]
            y_c = center_point[1]

            # Use affine transformation, so increase dimension by one.
            dummy_point = np.ones((bounds_pixel.shape[0], 1))

            # Move in parallel to the coordinates with the center as the origin
            bounds_affine = np.concatenate([bounds_pixel, dummy_point], axis=1)
            translation_matrix = np.array([[1,0,-x_c], [0,1,-y_c], [0,0,1]])

            bounds_trans = np.dot(translation_matrix, bounds_affine.T)

            # Rotate from center
            rotation_axis_matrix = self.rotation_axis_matrix_2d(theta, is_affine=True)
            bounds_trans_rotate = np.dot(rotation_axis_matrix, bounds_trans)

            # Move the lower left to the origin again
            after_center_point = np.array(polyline_image_rotate.size) / 2

            x_ca = after_center_point[0]
            y_ca = after_center_point[1]
            after_translation_matrix = np.array([[1,0,x_ca],[0,1,y_ca],[0,0,1]])

            bounds_after = np.dot(after_translation_matrix, bounds_trans_rotate).T
            bounds_after_2d = np.delete(bounds_after,-1,1)

            # use image
            use_image  = polyline_image_rotate
            use_bounds = bounds_after_2d

        else:
            use_image  = polyline_image
            use_bounds = bounds_pixel

                
        if draw_bounds:
            bounds_pixel_drow = np.concatenate([bounds_pixel, bounds_pixel[[0]]], axis=0)
            bounds_pixel_tuple = tuple(map(tuple, bounds_pixel_drow))

            draw = ImageDraw.Draw(polyline_image)
            draw.line(bounds_pixel_tuple, fill=(255, 0, 255), width=10)

        image_cv = self._pil2cv(use_image)

        # bounds is rounded to croped.
        # That is because, croped bound must be rounded bound. But drawn bounds is not rounded.
        use_bounds = use_bounds.round()
        use_bounds = use_bounds.astype(int)


        croped, mask, dst, dst2 = self.polygon_crop_cv(image_cv, use_bounds, mode='all')

        if crop_mode=='all':
            crop_mode=['croped', 'mask', 'dst', 'dst2']
        elif crop_mode!='all' and isinstance(crop_mode,str):
            crop_mode = [crop_mode]
            
        if crop_mode==False or crop_mode==None or crop_mode==[]:
            cv2.imwrite(save_path+'nocroped.png', image_cv)

        else:        
            if 'croped' in crop_mode:
                ## (1) Crop the bounding rect
                cv2.imwrite(save_path+'croped.png', croped)
            if 'mask' in crop_mode:
                ## (2) make mask
                cv2.imwrite(save_path+'mask.png', mask)
            if 'dst' in crop_mode:
                ## (3) do bit-op
                cv2.imwrite(save_path+'dst.png', dst)
            if 'dst2' in crop_mode:
                ## (4) add the white background
                cv2.imwrite(save_path+'dst2.png', dst2)

        # for check, return is exist.

        if return_check:
            return use_image





