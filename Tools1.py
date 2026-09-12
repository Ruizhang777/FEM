#- * -coding: UTF-8- * -
# chenhongcheng3097@163.com
# 2025-7-22 v1  XY238
# 2025-8-28 v2  XY238
# 2025-10-21 v3 XY238

from abaqus import *
from abaqusConstants import *
from textRepr import *
import mesh
import math
import itertools
import csv

"""
关于输出集合设置 （注意ODB文件中为大写）
1、结构监测点
1.1 注浆囊体【soil-1】 zjnt_hist_left_up/zjnt_hist_left_mid/zjnt_hist_left_down/zjnt_hist_right_up/zjnt_hist_right_mid/zjnt_hist_right_down
1.2 隧道【soil-1】 Tunnel_1_top/Tunnel_2_top_right45/Tunnel_3_right/Tunnel_4_right_bottom45/Tunnel_5_bottom/Tunnel_6_bottom_left45/Tunnel_7_left/Tunnel_8_left_up45
1.3 挡土墙【wall-zc-1】wall_Y_{自动索引}m

2、关键区域监测点
2.1 地表【soil-1】GS_X+{自动索引}m
2.2 基坑底部【soil-1】EB_X_{自动索引}m

3、密集监测区
3.1 挡土墙和隧道临近的矩形区域【soil-1】MJ-SD{单元编号}
3.2 地表向下2米，宽度同3.1【soil】MJ-DB{单元编号}
"""

def find_region_by_loc_tuple(find_region, aim_index_loc):

    exec("aim_region = find_region.findAt{}".format(aim_index_loc))
    return aim_region


def tools_get_whole_region(abaqus_object):

    aim_region = abaqus_object.getByBoundingBox(\
        xMin=-9999.9,\
        yMin=-9999.9,\
        zMin=-9999.9,\
        xMax=9999.9,\
        yMax=9999.9,\
        zMax=9999.9
        )
    return aim_region


class mdbProcess:
    """
    20250722 __version__1
    part1: chenqi
    part2: soil
    part3: wall-zc
    """
    def __init__(self, mn):
        """
        :param mn: model name
        """
        # user define para
        self.model_name = mn

        # abaqus api
        self.aim_model = None
        self.aim_assembly = None
        self.aim_part1 = None
        self.aim_part2 = None
        self.aim_part3_wall = None
        self.aim_part3_zc = None
        self.aim_part3_db = None
        self.aim_part3 = None  # wall和zc装配后的part

        # <用户不能修改以下参数> --------------------------------------------
        # part1 para || 取消
        self.part1_name = "chenqi"
        self.part1_ratio_inner = 2.75  # part1半径
        self.part1_ratio_out = 3.1  # part2半径
        self.half_ratio = (self.part1_ratio_inner+self.part1_ratio_out)*0.5  # 用于findAt

        # part2 para || 所有的坐标，除了part1以外(在装配过程移动)，均以part2挖孔的圆心坐标为基准
        self.part2_name = "soil"
        self.part2_len = 60.0  # part2长度-x方向
        self.part2_wid = 43.0  # part2宽度-y方向
        self.part2_circle_ratio = self.part1_ratio_inner  # part2挖孔半径
        self.part2_circle_x = 46.925  # part2挖孔-圆心-x坐标
        self.part2_circle_y = 21.50  # part2挖孔-圆心-y坐标
        self.part2_circle_cut_ratio = self.part1_ratio_out  # part2cut圆半径

        # <para>
        self.sjnt_x_loc_left = None  # 注浆囊体(胶囊)尺寸坐标索引
        self.sjnt_x_loc_right = None
        self.sjnt_y_loc_up = None
        self.sjnt_y_loc_down = None
        self.qw_x_loc_left = None # wall x坐标 左侧
        self.qw_x_loc_right = None # wall x坐标 右侧
        self.qw_y_loc_up =None  # wall y坐标 顶部
        self.qw_y_loc_down = None # wall y坐标 支撑的底部
        self.qw_y_loc_down_wall = None # wall y坐标 wall整体延伸下去的底部
        self.suidao_right_line_x_loc = None  # 隧道右侧竖线的x坐标
        self.suidao_right_line_y_loc_top = None  # 隧道右侧竖线的y顶部坐标
        self.suidao_right_line_y_loc_bottom = None  # 隧道右侧竖线的y底部坐标
        self.wall_index_loc_list = []

        # <index>
        self.part2_para_a = 6.1  # 请参考soil参数索引图
        self.part2_para_b = 6.1  # 请参考soil参数索引图
        self.part2_para_c = 0.15  # 请参考soil参数索引图
        self.part2_para_d = 9.875  # 请参考soil参数索引图
        self.part2_para_e = 0.8  # 请参考soil参数索引图
        self.part2_para_f = 3.0  # 请参考soil参数索引图
        self.part2_para_lc = 8.0  # 胶囊总高度
        self.part2_left_num = 8  # part2左侧结构，累计分切层数

        # part3 para
        self.part3_wall_name = "wall"
        self.part3_zc_name = "zc"
        self.part3_db_name = "db"
        self.part3_name = "wall-zc"
        self.part3_para_f = 3.0  # 开挖间距
        self.part3_db_thick_index = 1.0/3.0  # 底板厚度系数 (等于开挖间距的1/3)
        self.part3_db_thick = None  # 底板厚度 (生成部件时更新)
        self.part3_dtq_ratio_para = 1.5  # 20250814挡土墙高度是开挖深度的1.5倍
        self.db_left_x = None  # 底板左边界x
        self.db_left_y = None  # 底板底边界y
        self.db_right_x = None # 底板右边界x
        self.db_right_y = None # 底板顶边界y
        # <index>
        self.part3_left_num = 8  # part3左侧结构，累计分层数
        # 注：横梁数与开挖分层数一致
        self.part3_left_num2 = 8  # part3左侧结构，累计分层数(横梁数)
        # <para>
        self.wall_x_loc_left = None
        self.wall_x_loc_right = None
        self.zc_y_loc_list = []  # 支撑的y坐标索引列表

        # mesh para
        self.chenqi_mesh_size = 1.5
        self.soil_mesh_size = 1.0
        self.wall_zc_mesh_size = 1.0
        self.aim_region_chenqi = None  # 用于网格划分
        self.aim_region_soil = None  # 用于网格划分
        self.aim_region_soil_cq = None  # 用于网格划分
        self.aim_region_soil_sjnt = None  # 用于网格划分

        # hist out set name list
        self.tunnel_hist_set_name_list = []
        self.zjnt_hist_set_name_list = []
        self.wall_hist_set_name_lits = []
        self.GS_hist_set_name_list = []
        self.EB_hist_set_name_list = []
        self.MJ_hist_set_name_list = []
        
        # debug中间变量(不要改这里)
        self.dtq_height = None  # 挡土墙高度，(y坐标：self.part2_wid-self.dtq_height)，[兼] 用于分割soil两部分
        self.diban_heigt = None  # 底板高度，(yz坐标：self.db_left_y)，[兼] 用于分割soil两部分
        self.wall_y_down = None  # 切割线位置-[废弃]，新版self.soil2_find_y
        self.soil2_find_y = None  # soil2参数索引
        self.thred_number = 1e-3

    def set_whole_structure(self, part_len, part_wid):
        """
        设置整体结构参数
        """
        self.part2_len = part_len
        self.part2_wid = part_wid

    def set_suidao_para(self, Dt, Ht, tlining):
        """
        设置隧道参数 || 用户指定 || 参考：参数表1.pdf
        1、Dt-外径
        2、Dt和衬砌厚度tlining是已知参数
        3、Htaxis是随动参数，不计入
        """
        self.part1_ratio_out = Dt*0.5  # 隧道外径
        self.part2_circle_y = self.part2_wid-Ht-Dt*0.5  # 地表到隧道中心线(开挖深度)
        self.part1_ratio_inner = Dt*0.5-tlining

        # <更新变量>
        self.part2_circle_ratio = self.part1_ratio_inner
        self.part2_circle_cut_ratio = self.part1_ratio_out
        self.half_ratio = (self.part1_ratio_inner+self.part1_ratio_out)*0.5

    def set_jiaonang_para(self, Lct, Dc, Lc):
        """
        设置胶囊参数 || 用户指定 || 参考：参数表1
        1、胶囊初始直径Dc=0.2(与客户确认)
        2、胶囊膨胀后直径是计算过程参数决定的，与结构尺寸无关
        """
        self.part2_para_a = Lct + self.part1_ratio_out
        self.part2_para_c = Dc
        self.part2_para_lc = Lc

    def set_dangtu_para(self, Tw, Lwt, dtrt):
        """
        设置挡土墙参数 || 用户指定 || 参考：参数表1
        Hw参数可以不用
        """
        self.part2_para_e = Tw
        self.part2_para_d = Lwt-self.part2_para_a-self.part2_para_c
        self.part3_dtq_ratio_para = dtrt

    def set_kaiwa_para(self, He, F_B):
        """
        设置开挖参数 || 用户指定 || 参考：参数表1
        1、关于开挖深度：每3米挖一层，不整除，舍掉
        """
        self.part2_circle_x = F_B+self.part2_para_e+\
            self.part2_para_d+self.part2_para_c+self.part2_para_a

        self.part2_left_num = int(He//self.part2_para_f)
        self.part3_left_num = int(self.part2_left_num)
        self.part3_left_num2 = int(self.part2_left_num)

    def get_abaqus_object(self):

        # create a new model
        self.aim_model = mdb.Model(\
            name=self.model_name, modelType=STANDARD_EXPLICIT
            )

        self.aim_assembly = self.aim_model.rootAssembly

    def tools_create_part(self, part_name):
        """
        创建部件
        :return: part实例化对象
        """
        aim_part = self.aim_model.Part(\
            name=part_name, dimensionality=TWO_D_PLANAR, type=DEFORMABLE_BODY
            )

        return aim_part

    def tools_create_YZPLANE(self, aim_part, f_offset=0.0):
        """
        创建YZ基准面
        :return: 基准面实例化对象
        """
        aim_datumPlane = aim_part.DatumPlaneByPrincipalPlane(\
            principalPlane=YZPLANE, offset=f_offset
            )
        return aim_datumPlane

    def tools_create_XZPLANE(self, aim_part, f_offset=0.0):
        """
        创建XZ基准面
        :return: 基准面实例化对象
        """
        aim_datumPlane = aim_part.DatumPlaneByPrincipalPlane(\
            principalPlane=XZPLANE, offset=f_offset
            )
        return aim_datumPlane

    def tools_part_ring(self, aim_part, ratio_inner, ratio_out,\
        center_loc):
        """
        部件-创建单个圆环结构
        :param aim_part: part实例化对象
        :param ratio_inner: 内径
        :param ratio_out: 外径
        :param center_loc(x, y)
        """
        # scraft
        temp_scraft = self.aim_model.ConstrainedSketch(\
            name='__profile__', sheetSize=200.0
            )

        # 外径
        temp_scraft.CircleByCenterPerimeter(\
            center=(center_loc[0], center_loc[1]), \
            point1=(center_loc[0]+ratio_out, center_loc[1])
            )
        # 内径
        temp_scraft.CircleByCenterPerimeter(\
            center=(center_loc[0], center_loc[1]), \
            point1=(center_loc[0]+ratio_inner, center_loc[1])
            )

        aim_part.BaseShell(sketch=temp_scraft)

        # scraft
        del self.aim_model.sketches['__profile__']

    def tools_part_soil(self, aim_part):
        """
        部件-创建土体部分，中间还包含一个圆孔
        :param aim_part: part实例化对象
        """
        # scraft
        temp_scraft = self.aim_model.ConstrainedSketch(\
            name='__profile__', sheetSize=200.0
            )

        # 整体矩形
        temp_scraft.rectangle(\
            point1=(0.0, 0.0), \
            point2=(self.part2_len, self.part2_wid)
            )
#
#        # 挖孔圆形
#        temp_scraft.CircleByCenterPerimeter(\
#            center=(self.part2_circle_x, self.part2_circle_y), \
#            point1=(self.part2_circle_x+self.part2_circle_ratio, \
#            self.part2_circle_y)
#            )

        aim_part.BaseShell(sketch=temp_scraft)

        # scraft
        del self.aim_model.sketches['__profile__']

    def tools_part_wall(self, aim_part):
        """
        部件-创建wall部分 || 匹配soil空间位置
        """
        # scraft
        temp_scraft = self.aim_model.ConstrainedSketch(\
            name='__profile__', sheetSize=200.0
            )

        # 计算坐标
        left_down_x = self.part2_circle_x-self.part2_para_a-self.part2_para_c\
            -self.part2_para_d-self.part2_para_e
        left_down_y = self.part2_wid-self.part3_left_num*self.part3_para_f
        right_up_x = self.part2_circle_x-self.part2_para_a-self.part2_para_c\
            -self.part2_para_d
        right_up_y = self.part2_wid

        # <20250813>
        self.dtq_height = (self.part3_left_num*self.part3_para_f)*self.part3_dtq_ratio_para
        left_down_y_wall = self.part2_wid-self.dtq_height

        # <para>
        self.wall_x_loc_left = left_down_x
        self.wall_x_loc_right = right_up_x
        self.qw_y_loc_down_wall = left_down_y_wall

        # 整体矩形
        temp_scraft.rectangle(\
            point1=(left_down_x, left_down_y_wall), \
            point2=(right_up_x, right_up_y)
            )

        aim_part.BaseShell(sketch=temp_scraft)

        # scraft
        del self.aim_model.sketches['__profile__']

        return left_down_x, left_down_y, right_up_x, right_up_y

    def tools_part_zc(self, aim_part):
        """
        部件-创建zc部分 || 匹配soil空间位置
        三维线
        """
        # scraft
        temp_scraft = self.aim_model.ConstrainedSketch(\
            name='__profile__', sheetSize=200.0
            )

        # 计算坐标
        left_start_x = 0.0
        right_start_x = self.part2_circle_x-self.part2_para_a-self.part2_para_c\
            -self.part2_para_d-self.part2_para_e
        start_y = self.part2_wid

        # 二维线
        for i in range(self.part3_left_num2):  # 算顶边，不算底边 <20250813>
            temp_scraft.Line(\
                point1=(left_start_x, start_y-self.part3_para_f*i),\
                point2=(right_start_x, start_y-self.part3_para_f*i)
                )
            self.zc_y_loc_list.append(start_y-self.part3_para_f*i)

        aim_part.BaseWire(sketch=temp_scraft)

        # scraft
        del self.aim_model.sketches['__profile__']
        
    def tools_part_db(self, aim_part):
        """
        部件-创建db部分 || 匹配soil空间位置
        """
        self.part3_db_thick = self.part3_para_f*self.part3_db_thick_index
        self.db_left_x = 0.0
        self.db_left_y = self.part2_wid - (self.part3_left_num*self.part3_para_f)
        self.db_right_x = self.part2_circle_x-self.part2_para_a-self.part2_para_c\
            -self.part2_para_d
        self.db_right_y = self.db_left_y + self.part3_db_thick

        self.diban_heigt = self.db_left_y
        
        # scraft
        temp_scraft = self.aim_model.ConstrainedSketch(\
            name='__profile__', sheetSize=200.0
            )
        
        # db矩形
        temp_scraft.rectangle(\
            point1=(self.db_left_x, self.db_left_y), \
            point2=(self.db_right_x, self.db_right_y)
            )

        aim_part.BaseShell(sketch=temp_scraft)  
        
        # scraft
        del self.aim_model.sketches['__profile__']
        
    def tools_instance_from_part(self, part_name, instance_name):
        """
        create instance form part
        """
        aim_part = self.aim_model.parts[part_name]
        self.aim_assembly.Instance(\
            name=instance_name, part=aim_part, dependent=ON
            )

    def part1_chenqi(self):
        """
        part1 process || chenqi || part1坐标在装配体中修改
        """
        def cut_part(f_aim_face, aim_datum, f_aim_part1, find_loc,\
            datum_object):
            # finaAt
            f_aim_region = f_aim_face.findAt(\
                (find_loc,))
            # datum id
            datum_id = int(datum_object.id)
            # part cut
            f_aim_part1.PartitionFaceByDatumPlane(\
                datumPlane=aim_datum[datum_id], faces=f_aim_region
                )

        # 1 创建部件 || aim_part1
        self.aim_part1 = self.tools_create_part(\
            self.part1_name
            )

        # 2 创建环形结构
        self.tools_part_ring(\
            aim_part=self.aim_part1, \
            ratio_inner=self.part1_ratio_inner, \
            ratio_out=self.part1_ratio_out, \
            center_loc=(0.0, 0.0)
            )

        # <切分> --------------------------------------------------------
        # 3 创建部件切分基准面
        YZ_datumPlane = self.tools_create_YZPLANE(self.aim_part1)
        XZ_datumPlane = self.tools_create_XZPLANE(self.aim_part1)

        # get aim face & aim datum
        aim_face = self.aim_part1.faces
        aim_datum = self.aim_part1.datums

        # 4 第一次沿XZ plane切分整体
        cut_part(\
            aim_face, aim_datum, self.aim_part1, \
            find_loc=(-self.half_ratio, 0.0, 0.0), \
            datum_object=XZ_datumPlane
            )

        # 4 第二次先切分上半圆环、再切分下半圆环
        # 4.1 上半圆环
        cut_part(\
            aim_face, aim_datum, self.aim_part1, \
            find_loc=(0.0, self.half_ratio, 0.0), \
            datum_object=YZ_datumPlane
            )

        # 4.2 下半圆环
        cut_part(\
            aim_face, aim_datum, self.aim_part1, \
            find_loc=(0.0, -self.half_ratio, 0.0), \
            datum_object=YZ_datumPlane
            )

    def part2_soil(self):
        """
        part2 process || soil
        """
        def create_edge_set(ap, ae, findAt_loc, set_name):
            """
            findAt_loc: ((x, y, z), )
            """
            edge_region = ae.findAt(findAt_loc)
            ap.Set(edges=edge_region, name=set_name)
            return None

        def create_edge_set_double(ap, ae, findAt_loc1, findAt_loc2, set_name):
            """
            findAt_loc: ((x, y, z), )
            """
            edge_region = ae.findAt(findAt_loc1, findAt_loc2)
            ap.Set(edges=edge_region, name=set_name)
            return None

        # 1 创建部件 || aim_part2
        self.aim_part2 = self.tools_create_part(\
            self.part2_name
            )

        # 2 创建整体矩形
        self.tools_part_soil(self.aim_part2)

        # <集合> --------------------------------------------------------
        # 2.1 两侧的x/y集合
        create_edge_set_double(\
            self.aim_part2, self.aim_part2.edges, \
            ((0.0, self.part2_wid*0.5, 0.0), ),
            ((self.part2_len, self.part2_wid*0.5, 0.0),), "X"
            )

        create_edge_set(\
            self.aim_part2, self.aim_part2.edges, \
            ((self.part2_len*0.5, 0.0, 0.0),), "Y"
            )
        # <集合> --------------------------------------------------------

        # 3 切分(通过草图切分)
        # transform side
        aim_faces = self.aim_part2.faces
        aim_edges = self.aim_part2.edges

        # 选择表面(只要不在圆孔覆盖的区域就好，这里设置中心点)
        aim_face_region = aim_faces.findAt(\
            ((self.part2_len*0.5, self.part2_wid*0.5, 0.0))
            )
        aim_face_id = int(aim_face_region.index)

        # 选择边缘(选择右侧边)
        aim_edge_region = aim_edges.findAt(\
            ((self.part2_len, self.part2_wid*0.5, 0.0))
            )
        aim_edge_id = int(aim_edge_region.index)

        # aim transform
        aim_transform = self.aim_part2.MakeSketchTransform(\
            sketchPlane=aim_faces[aim_face_id], \
            sketchUpEdge=aim_edges[aim_edge_id], \
            sketchPlaneSide=SIDE1, \
            origin=(0.0, 0.0, 0.0)
            )

        # scraft || with transform
        aim_scraft = self.aim_model.ConstrainedSketch(name='__profile__',
            sheetSize=200.0, transform=aim_transform)

        self.aim_part2.projectReferencesOntoSketch(\
            sketch=aim_scraft, filter=COPLANAR_EDGES
            )

        # cut - 1 - 圆环外圈
        aim_scraft.CircleByCenterPerimeter(\
            center=(self.part2_circle_x, self.part2_circle_y), \
            point1=(self.part2_circle_x+self.part2_circle_cut_ratio, \
            self.part2_circle_y)
            )

        # cut - 2 - 右侧结构 (竖向切割线*4；横向切割线*3)
        # 右侧结构-竖向切割线-左1
        x_loc = self.part2_circle_x-self.part2_para_a-self.part2_para_c
        aim_scraft.Line(\
            point1=(x_loc, 0.0), \
            point2=(x_loc, self.part2_wid)
            )
        # 右侧结构-竖向切割线-左2
        x_loc = self.part2_circle_x-self.part2_para_a
        aim_scraft.Line(\
            point1=(x_loc, 0.0), \
            point2=(x_loc, self.part2_wid)
            )
        # 右侧结构-竖向切割线-左3
        x_loc = self.part2_circle_x
        aim_scraft.Line(\
            point1=(x_loc, 0.0), \
            point2=(x_loc, self.part2_wid)
            )
        # 右侧结构-竖向切割线-左4
        x_loc = self.part2_circle_x + self.part2_para_a
        aim_scraft.Line(\
            point1=(x_loc, 0.0), \
            point2=(x_loc, self.part2_wid)
            )
        self.suidao_right_line_x_loc = x_loc

        # 右侧结构-横向切割线-上1
        x_loc_left = self.part2_circle_x-self.part2_para_a-self.part2_para_c
        x_loc_right = self.part2_len
        y_loc = self.part2_circle_y+self.part2_para_b
        aim_scraft.Line(\
            point1=(x_loc_left, y_loc), \
            point2=(x_loc_right, y_loc)
            )
        self.suidao_right_line_y_loc_top = y_loc
        # 右侧结构-横向切割线-上2
        y_loc = self.part2_circle_y
        aim_scraft.Line(\
            point1=(x_loc_left, y_loc), \
            point2=(x_loc_right, y_loc)
            )
        # 右侧结构-横向切割线-上3
        y_loc = self.part2_circle_y-self.part2_para_b
        aim_scraft.Line(\
            point1=(x_loc_left, y_loc), \
            point2=(x_loc_right, y_loc)
            )
        self.suidao_right_line_y_loc_bottom = y_loc

        # 右侧结构-胶囊-顶部
        self.sjnt_x_loc_left = self.part2_circle_x-self.part2_para_a-self.part2_para_c
        self.sjnt_x_loc_right = self.part2_circle_x-self.part2_para_a
        self.sjnt_y_loc_up = self.part2_circle_y+self.part2_para_lc*0.5
        aim_scraft.Line(\
            point1=(self.sjnt_x_loc_left, self.sjnt_y_loc_up), \
            point2=(self.sjnt_x_loc_right, self.sjnt_y_loc_up)
            )

        # 右侧结构-胶囊-底部
        self.sjnt_y_loc_down = self.part2_circle_y-self.part2_para_lc*0.5
        aim_scraft.Line(\
            point1=(self.sjnt_x_loc_left, self.sjnt_y_loc_down), \
            point2=(self.sjnt_x_loc_right, self.sjnt_y_loc_down)
            )

        # cut - 3 - 左侧结构 (竖向切割线*2；横向切割线*n())
        # 左侧结构-竖向切割线-左1
        x_loc = self.part2_circle_x-self.part2_para_a-self.part2_para_c-self.part2_para_d\
            -self.part2_para_e
        self.qw_x_loc_left = x_loc

        aim_scraft.Line(\
            point1=(x_loc, 0.0), \
            point2=(x_loc, self.part2_wid)
            )
        # 左侧结构-竖向切割线-左2
        x_loc = self.part2_circle_x-self.part2_para_a-self.part2_para_c-self.part2_para_d
        self.qw_x_loc_right = x_loc

        aim_scraft.Line(\
            point1=(x_loc, 0.0), \
            point2=(x_loc, self.part2_wid)
            )
        # 左侧结构-横向切割线
        x_loc_left = 0.0
        x_loc_right = self.part2_circle_x-self.part2_para_a-self.part2_para_c-self.part2_para_d

        index_num = 0
        y_loc_list = [self.part2_wid]
        while index_num < self.part2_left_num:
            index_num+=1
            y_loc = self.part2_wid-index_num*self.part2_para_f
            aim_scraft.Line(\
                point1=(x_loc_left, y_loc), \
                point2=(x_loc_right, y_loc)
                )
            y_loc_list.append(y_loc)

#        # <20250813>
#        wall_x_loc_left = x_loc_right-self.part2_para_e
#        wall_x_loc_right = x_loc_right
#        wall_y_down = self.part2_wid-self.dtq_height
#
#        aim_scraft.Line(\
#            point1=(wall_x_loc_left, wall_y_down), \
#            point2=(wall_x_loc_right, wall_y_down)
#            )

        # <20251020> 之前wall-zc底边基础上，延长成贯穿整个模型的分割线
        wall_x_loc_left = 0.0
        wall_x_loc_right = self.part2_len

        # <判定切分线位置> 1- 如果底板底部比隧道下方切割线底部低，则切分线与底板底部平行
        if self.diban_heigt < self.part2_circle_y-self.part2_para_b:

            self.wall_y_down = self.diban_heigt
            aim_scraft.Line(\
                point1=(wall_x_loc_left, self.wall_y_down), \
                point2=(wall_x_loc_right, self.wall_y_down)
                )

            self.soil2_find_y = self.wall_y_down
            
            # 挡土墙底部切分
            wall_x_loc_left = x_loc_right-self.part2_para_e
            wall_x_loc_right = x_loc_right
            aim_scraft.Line(\
                point1=(wall_x_loc_left, self.part2_wid-self.dtq_height), \
                point2=(wall_x_loc_right, self.part2_wid-self.dtq_height)
                )

        # <判定切分线位置> 2- 如果隧道下方切割线位于底板下方，但是位于挡土墙上方，则切分线与挡土墙底部平行
        elif self.part2_wid-self.dtq_height < self.part2_circle_y-self.part2_para_b:
            
            self.wall_y_down = self.part2_wid-self.dtq_height
            aim_scraft.Line(\
                point1=(wall_x_loc_left, self.wall_y_down), \
                point2=(wall_x_loc_right, self.wall_y_down)
                )

            self.soil2_find_y = self.wall_y_down

        # <判定切分线位置> 3- 否则，切分线位于隧道下方切割线再下边1米，同时挡土墙下边也要做切分
        else:
            self.wall_y_down = self.part2_circle_y-self.part2_para_b-1.0
            aim_scraft.Line(\
                point1=(wall_x_loc_left, self.wall_y_down), \
                point2=(wall_x_loc_right, self.wall_y_down)
                )
            
            self.soil2_find_y = self.wall_y_down

            # 挡土墙底部切分
            wall_x_loc_left = x_loc_right-self.part2_para_e
            wall_x_loc_right = x_loc_right
            aim_scraft.Line(\
                point1=(wall_x_loc_left, self.part2_wid-self.dtq_height), \
                point2=(wall_x_loc_right, self.part2_wid-self.dtq_height)
                )

        # 用于创建wall集合
        x_centrol_loc = (x_loc_left+x_loc_right)*0.5
        for k in range(len(y_loc_list)-1):
            y_centrol_loc = (y_loc_list[k]+y_loc_list[k+1])*0.5
            self.wall_index_loc_list.append(\
                [x_centrol_loc, y_centrol_loc]
                )

        self.qw_y_loc_up = self.part2_wid
        self.qw_y_loc_down = y_loc

        # pickface
        pickedFaces = aim_face_region
        self.aim_part2.PartitionFaceBySketch(\
            sketchUpEdge=aim_edges[aim_edge_id], faces=pickedFaces, sketch=aim_scraft
            )

        # scraft
        del self.aim_model.sketches['__profile__']

    def part3_wall_zc(self):
        """
        wall和zc分开创建part，然后再布尔
        """
        def cut_part(f_aim_face, aim_datum, f_aim_part1, find_loc,\
            datum_object):
            # finaAt
            f_aim_region = f_aim_face.findAt(\
                (find_loc,))
            # datum id
            datum_id = int(datum_object.id)
            # part cut
            f_aim_part1.PartitionFaceByDatumPlane(\
                datumPlane=aim_datum[datum_id], faces=f_aim_region
                )

        # 1 wall部分
        # 1.1 创建部件 || aim_part3
        self.aim_part3_wall = self.tools_create_part(\
            self.part3_wall_name
            )

        # 1.2 创建整体矩形
        left_down_x, left_down_y, right_up_x, right_up_y = \
            self.tools_part_wall(self.aim_part3_wall)

        # get aim face & aim datum
        aim_face = self.aim_part3_wall.faces
        aim_datum = self.aim_part3_wall.datums

        # 1.3 切分(通过基准面偏移)
        # 索引点(始终选择最下端不会被切到的部分)
        index_f_x = (left_down_x+right_up_x)*0.5
        index_f_y = ((self.part2_wid-self.part3_left_num*self.part3_para_f)+\
            (self.part2_wid-(self.part3_left_num-1)*self.part3_para_f))*0.5

        # 对于每一层
        for i in range(self.part3_left_num):  # 最后一层需要切<20250813>

            # 基准面偏移值
            datum_offset = self.part2_wid-self.part3_para_f*(i+1)

            # 创建偏移基准面
            XZ_datumPlane = self.tools_create_XZPLANE(\
                self.aim_part3_wall, f_offset=datum_offset
                )

            # 执行分切
            cut_part(\
                aim_face, aim_datum, self.aim_part3_wall, \
                find_loc=(index_f_x, index_f_y, 0.0), \
                datum_object=XZ_datumPlane
                )

        # ----------------------------------------------------------------------
        # 2 zc部分
        # 2.1 创建部分 || aim_part3
        self.aim_part3_zc = self.tools_create_part(\
            self.part3_zc_name
            )

        # 2.2 创建三维线
        self.tools_part_zc(self.aim_part3_zc)
        
        # ----------------------------------------------------------------------
        # 3 db底板部分
        # 3.1 创建部件
        self.aim_part3_db = self.tools_create_part(\
            self.part3_db_name
            )
        
        # 3.2 创建矩形
        # 1.2 创建整体矩形
        self.tools_part_db(self.aim_part3_db)

        # ----------------------------------------------------------------------
        # 4 布尔获得wall-zc
        self.tools_instance_from_part(\
            part_name=self.part3_wall_name, instance_name="{}-1".format(self.part3_wall_name)
            )

        self.tools_instance_from_part(\
            part_name=self.part3_zc_name, instance_name="{}-1".format(self.part3_zc_name)
            )
            
        self.tools_instance_from_part(\
            part_name=self.part3_db_name, instance_name="{}-1".format(self.part3_db_name)
            )

        self.aim_assembly.InstanceFromBooleanMerge(\
            name=self.part3_name, \
            instances=(\
            self.aim_assembly.instances["{}-1".format(self.part3_wall_name)], \
            self.aim_assembly.instances["{}-1".format(self.part3_zc_name)], \
            self.aim_assembly.instances["{}-1".format(self.part3_db_name)]), \
            keepIntersections=ON, \
            originalInstances=DELETE, domain=GEOMETRY
            )

        self.aim_part3 = self.aim_model.parts[self.part3_name]

    def part1_set(self):

        # <集合> --------------------------------------------------------
        # 创建chenqi的cq-all集合
        # 圆环第一象限中心点坐标
        half_num = self.half_ratio*sqrt(2.0)*0.5  # 表面-第一象限索引点

        aim_faces = self.aim_part1.faces

        face_region = aim_faces.findAt(\
            ((half_num, half_num, 0.0), ),
            ((-half_num, half_num, 0.0), ),
            ((-half_num, -half_num, 0.0), ),
            ((half_num, -half_num, 0.0), )
            )
        self.aim_region_chenqi = face_region

        self.aim_part1.Set(\
            faces=face_region, name='cq-all'
            )

    def part1_surface(self):

        # <表面> --------------------------------------------------------
        # 6 创建chenqi的cq-soil表面
        half_num = self.part1_ratio_out*sqrt(2.0)*0.5

        aim_sidEdges = self.aim_part1.edges

        sideEdge_region = aim_sidEdges.findAt(\
            ((half_num, half_num, 0.0), ),
            ((-half_num, half_num, 0.0), ),
            ((-half_num, -half_num, 0.0), ),
            ((half_num, -half_num, 0.0), )
            )

        self.aim_part1.Surface(\
            side1Edges=sideEdge_region, name='cq-soil'
            )

    def part2_set(self):

        # <集合> -------------------------------------------------------
        # 1 胶囊集合
        aim_faces = self.aim_part2.faces
        face_region = aim_faces.getByBoundingBox(\
            xMin=self.sjnt_x_loc_left, \
            yMin=self.sjnt_y_loc_down, \
            zMin=0.0, \
            xMax=self.sjnt_x_loc_right, \
            yMax=self.sjnt_y_loc_up, \
            zMax=0.0
            )
        self.aim_region_soil_sjnt = face_region
        self.aim_part2.Set(faces=face_region, name='sjnt')

        # <集合> -------------------------------------------------------
        # 2 soil集合
        face_region_total = aim_faces.getByBoundingBox(\
            xMin=0.0, \
            yMin=0.0, \
            zMin=0.0, \
            xMax=self.part2_len, \
            yMax=self.part2_wid, \
            zMax=0.0
            )

        face_region_sjnt = aim_faces.getByBoundingBox(\
            xMin=self.sjnt_x_loc_left, \
            yMin=self.sjnt_y_loc_down, \
            zMin=0.0, \
            xMax=self.sjnt_x_loc_right, \
            yMax=self.sjnt_y_loc_up, \
            zMax=0.0
            )
        sjnt_index_list = [ite.index for ite in face_region_sjnt]

#        face_region_sd = aim_faces.getByBoundingSphere(\
#            center=(self.part2_circle_x, self.part2_circle_y, 0.0), \
#            radius=self.part1_ratio_out*1.0001
#            )
#        sd_index_list = [ite.index for ite in face_region_sd]

        aim_index_loc = ()  # ()
        for ite in face_region_total:
            index_num = ite.index
            if index_num in sjnt_index_list:
                continue
#            if index_num in sd_index_list:
#                continue
            aim_index_loc += ((ite.pointOn[0],),)

        # find aim region
        aim_region = find_region_by_loc_tuple(aim_faces, aim_index_loc)
        self.aim_region_soil = aim_region

        self.aim_part2.Set(faces=aim_region, name='soil')
        
        # <集合> -------------------------------------------------------
        # 2补充 soil-1集合 (上边)
        face_region_total = aim_faces.getByBoundingBox(\
            xMin=0.0, \
            yMin=self.soil2_find_y, \
            zMin=0.0, \
            xMax=self.part2_len, \
            yMax=self.part2_wid, \
            zMax=0.0
            )
            
        aim_index_loc = ()  # ()
        for ite in face_region_total:
            index_num = ite.index
            if index_num in sjnt_index_list:
                continue
            aim_index_loc += ((ite.pointOn[0],),)

        # find aim region
        aim_region = find_region_by_loc_tuple(aim_faces, aim_index_loc)

        self.aim_part2.Set(faces=aim_region, name='soil-1')
        
        # <集合> -------------------------------------------------------
        # 2补充 soil-2集合 (下边)
        face_region_total = aim_faces.getByBoundingBox(\
            xMin=0.0, \
            yMin=0.0, \
            zMin=0.0, \
            xMax=self.part2_len, \
            yMax=self.soil2_find_y, \
            zMax=0.0
            )
            
        aim_index_loc = ()  # ()
        for ite in face_region_total:
            index_num = ite.index
            if index_num in sjnt_index_list:
                continue
            aim_index_loc += ((ite.pointOn[0],),)

        # find aim region
        aim_region = find_region_by_loc_tuple(aim_faces, aim_index_loc)

        self.aim_part2.Set(faces=aim_region, name='soil-2')
#
#        # <集合> -------------------------------------------------------
#        # 3 soil-cq集合
#        face_region_sd = aim_faces.getByBoundingSphere(\
#            center=(self.part2_circle_x, self.part2_circle_y, 0.0), \
#            radius=self.part1_ratio_out*1.0001
#            )
#        self.aim_part2.Set(faces=face_region_sd, name='soil-cq')

        # <集合> -------------------------------------------------------
        # 4 soil-qw集合
        
        # qw部分
        face_region_qw = aim_faces.getByBoundingBox(\
            xMin=self.qw_x_loc_left, \
            yMin=self.qw_y_loc_down_wall, \
            zMin=0.0, \
            xMax=self.qw_x_loc_right, \
            yMax=self.qw_y_loc_up, \
            zMax=0.0
            )
        self.aim_region_soil_cq = face_region_qw
        
        # <20251020> 右侧开挖部分
        face_region_sd = aim_faces.getByBoundingSphere(\
            center=(self.part2_circle_x, self.part2_circle_y, 0.0),
            radius=self.part1_ratio_out+self.thred_number,
            )
        
        face_region = face_region_qw + face_region_sd
        for k in range(len(self.wall_index_loc_list)):
            ite = self.wall_index_loc_list[k]
            face_region += aim_faces.findAt(\
                ((ite[0], ite[1], 0.0), )
                )

        self.aim_part2.Set(faces=face_region, name='soil-qw')

    def part2_surface(self):

        # <表面> -------------------------------------------------------
        aim_edges = self.aim_part2.edges

        # 1 soil-wall-r表面
        ite_x_loc = self.qw_x_loc_right

        aim_index_loc = ()
        for k in range(len(self.wall_index_loc_list)):
            ite_y_loc = self.wall_index_loc_list[k][1]
            aim_index_loc += (((ite_x_loc, ite_y_loc, 0.0),),)

        # <20250813>
        aim_index_loc += ((\
            (ite_x_loc, (self.qw_y_loc_down_wall+self.qw_y_loc_down)*0.5, 0.0)\
            ,),)

        side1Edges = find_region_by_loc_tuple(aim_edges, aim_index_loc)
        self.aim_part2.Surface(side1Edges=side1Edges, name='soil-wall-r')

        # 2 soil-chengqi表面 (已知圆心和半径，四个象限各找一个点)
        ite_R = (sqrt(2.0)*0.5)*self.part1_ratio_out

        aim_index_loc = (\
            ((self.part2_circle_x+ite_R, self.part2_circle_y+ite_R, 0.0),),
            ((self.part2_circle_x-ite_R, self.part2_circle_y+ite_R, 0.0),),
            ((self.part2_circle_x-ite_R, self.part2_circle_y-ite_R, 0.0),),
            ((self.part2_circle_x+ite_R, self.part2_circle_y-ite_R, 0.0),),
            )

        side2Edges = find_region_by_loc_tuple(aim_edges, aim_index_loc)
        self.aim_part2.Surface(side2Edges=side2Edges, name='soil-chenqi')

        # 3 soil-wall-di表面
        ite_x_loc = (self.wall_x_loc_left+self.wall_x_loc_right)*0.5
        ite_y_loc = self.zc_y_loc_list[-1]

        aim_index_loc = (\
            ((ite_x_loc, ite_y_loc, 0.0),),
            )

        side2Edges = find_region_by_loc_tuple(aim_edges, aim_index_loc)
        self.aim_part2.Surface(side2Edges=side2Edges, name='soil-wall-di')

        # 4 soil-wall-lx表面
        for k in range(len(self.wall_index_loc_list)):
            ite = self.wall_index_loc_list[k]
            side1Edges = aim_edges.findAt(\
                ((self.wall_x_loc_left, ite[1], 0.0), )
                )
            self.aim_part2.Surface(side1Edges=side1Edges, name='soil-wall-l{}'.format(k))

    def part2_surface_v2(self):

        # <表面> -------------------------------------------------------
        aim_edges = self.aim_part2.edges

        # 1 wall-soil
        # 1.1 wall-soil_di 区域
        ite_x_loc = (self.wall_x_loc_left+self.wall_x_loc_right)*0.5
        ite_y_loc = self.qw_y_loc_down_wall

        aim_index_loc = (\
            ((ite_x_loc, ite_y_loc, 0.0),),
            )

        # 1.2 wall-soil-r 区域
        ite_x_loc = self.qw_x_loc_right

        for k in range(len(self.wall_index_loc_list)):
            ite_y_loc = self.wall_index_loc_list[k][1]
            aim_index_loc += (((ite_x_loc, ite_y_loc, 0.0),),)

        # <20250813>
        aim_index_loc += ((\
            (ite_x_loc, (self.qw_y_loc_down_wall+self.qw_y_loc_down)*0.5, 0.0)\
            ,),)
            
        # <20251020>
        aim_index_loc += ((\
            ((0.0+self.wall_x_loc_left)*0.5, self.qw_y_loc_down, 0.0)\
            ,),)

        # 1.3 wall-soil-left 区域
        aim_index_loc += ((\
            (self.wall_x_loc_left, (self.qw_y_loc_down_wall+self.qw_y_loc_down)*0.5, 0.0),),)

        aim_edge = find_region_by_loc_tuple(aim_edges, aim_index_loc)
        self.aim_part2.Surface(side2Edges=aim_edge, name='wall-soil')

        # 2 yaqiang1
        x_loc = self.sjnt_x_loc_left
        y_loc1 = self.sjnt_y_loc_up-(self.sjnt_y_loc_up - self.sjnt_y_loc_down)*0.25  # 1/4索引点
        y_loc2 = self.sjnt_y_loc_up-(self.sjnt_y_loc_up - self.sjnt_y_loc_down)*0.75  # 3/4索引点
        aim_index_loc = (((x_loc, y_loc1, 0.0),), ((x_loc, y_loc2, 0.0),),)
        aim_edge = find_region_by_loc_tuple(aim_edges, aim_index_loc)
        self.aim_part2.Surface(side2Edges=aim_edge, name='yaqiang1')

        # 3 yaqiang2
        x_loc = self.sjnt_x_loc_right
        y_loc1 = self.sjnt_y_loc_up-(self.sjnt_y_loc_up - self.sjnt_y_loc_down)*0.25  # 1/4索引点
        y_loc2 = self.sjnt_y_loc_up-(self.sjnt_y_loc_up - self.sjnt_y_loc_down)*0.75  # 3/4索引点
        aim_index_loc = (((x_loc, y_loc1, 0.0),), ((x_loc, y_loc2, 0.0),),)
        aim_edge = find_region_by_loc_tuple(aim_edges, aim_index_loc)
        self.aim_part2.Surface(side1Edges=aim_edge, name='yaqiang2')

        # 4 chenqi表面
        #soil-chengqi表面 (已知圆心和半径，四个象限各找一个点)
        ite_R = (sqrt(2.0)*0.5)*self.part1_ratio_out

        aim_index_loc = (\
            ((self.part2_circle_x+ite_R, self.part2_circle_y+ite_R, 0.0),),
            ((self.part2_circle_x-ite_R, self.part2_circle_y+ite_R, 0.0),),
            ((self.part2_circle_x-ite_R, self.part2_circle_y-ite_R, 0.0),),
            ((self.part2_circle_x+ite_R, self.part2_circle_y-ite_R, 0.0),),
            )

        side2Edges = find_region_by_loc_tuple(aim_edges, aim_index_loc)
        self.aim_part2.Surface(side2Edges=side2Edges, name='soil-chenqi')

    def part3_set(self):

        # <集合> -------------------------------------------------------
        aim_faces = self.aim_part3.faces
        aim_edges = self.aim_part3.edges
        aim_vertices = self.aim_part3.vertices

        # wall-all 集合
        face_region = aim_faces.getByBoundingBox(\
            xMin=self.qw_x_loc_left, \
            yMin=self.qw_y_loc_down_wall, \
            zMin=0.0, \
            xMax=self.qw_x_loc_right, \
            yMax=self.qw_y_loc_up, \
            zMax=0.0
            )
        self.aim_part3.Set(faces=face_region, name='wall-all')

        # zc-all集合
        ite_x_loc = (0.0+self.qw_x_loc_left)*0.5
        aim_index_loc = ()
        for k in range(len(self.zc_y_loc_list)):
            ite_y_loc = self.zc_y_loc_list[k]
            aim_index_loc += (((ite_x_loc, ite_y_loc, 0.0),),)

        edges = find_region_by_loc_tuple(aim_edges, aim_index_loc)
        self.aim_part3.Set(edges=edges, name='za-all')

        # zc-x集合
        aim_index_loc = ()
        for k in range(len(self.zc_y_loc_list)):
            ite_y_loc = self.zc_y_loc_list[k]
            aim_index_loc += (((0.0, ite_y_loc, 0.0),),)

        verts = find_region_by_loc_tuple(aim_vertices, aim_index_loc)
        self.aim_part3.Set(vertices=verts, name='zc-x')

        # zc集合
        ite_x_loc = (0.0+self.qw_x_loc_left)*0.5
        for k in range(len(self.zc_y_loc_list)):
            ite_y_loc = self.zc_y_loc_list[k]
            aim_index_loc = (((ite_x_loc, ite_y_loc, 0.0),),)

            edges = find_region_by_loc_tuple(aim_edges, aim_index_loc)
            self.aim_part3.Set(edges=edges, name='zc{}'.format(k))

    def part3_set_v2(self):

        # <集合> -------------------------------------------------------
        aim_faces = self.aim_part3.faces
        aim_edges = self.aim_part3.edges
        aim_vertices = self.aim_part3.vertices

        # wall 集合
        face_region_wall = aim_faces.getByBoundingBox(\
            xMin=self.qw_x_loc_left, \
            yMin=self.qw_y_loc_down_wall, \
            zMin=0.0, \
            xMax=self.qw_x_loc_right, \
            yMax=self.qw_y_loc_up, \
            zMax=0.0
            )
        self.aim_part3.Set(faces=face_region_wall, name='wall')
        
        # diban 集合
        face_region_db = aim_faces.getByBoundingBox(\
            xMin=self.db_left_x, \
            yMin=self.db_left_y, \
            zMin=0.0, \
            xMax=self.qw_x_loc_left, \
            yMax=self.db_right_y, \
            zMax=0.0
            )
        self.aim_part3.Set(faces=face_region_db, name='diban')

        # wall-all集合
        ite_x_loc = (0.0+self.qw_x_loc_left)*0.5
        aim_index_loc = ()
        for k in range(len(self.zc_y_loc_list)):
            ite_y_loc = self.zc_y_loc_list[k]
            aim_index_loc += (((ite_x_loc, ite_y_loc, 0.0),),)

        edges = find_region_by_loc_tuple(aim_edges, aim_index_loc)
        self.aim_part3.Set(edges=edges, faces=face_region_wall+face_region_db, name='wall-all')

        # zc-x集合
        aim_index_loc = ()
        for k in range(len(self.zc_y_loc_list)):
            ite_y_loc = self.zc_y_loc_list[k]
            aim_index_loc += (((0.0, ite_y_loc, 0.0),),)

        # <20251021> 增加底板部分
        aim_edge = aim_edges.findAt(((self.db_left_x, (self.db_left_y+self.db_right_y)*0.5, 0.0), ))

        verts = find_region_by_loc_tuple(aim_vertices, aim_index_loc)
        self.aim_part3.Set(vertices=verts, edges=aim_edge, name='zc-x')

        # zc-c集合
        ite_y_loc = self.zc_y_loc_list[0]
        aim_index_loc = (((ite_x_loc, ite_y_loc, 0.0),),)

        edges_zc_c = find_region_by_loc_tuple(aim_edges, aim_index_loc)
        self.aim_part3.Set(edges=edges_zc_c, name='zc-c')
        
        # zc-gang集合
        ite_x_loc = (0.0+self.qw_x_loc_left)*0.5
        aim_index_loc = ()
        for k in range(len(self.zc_y_loc_list)):
            if k==0:
                continue
            ite_y_loc = self.zc_y_loc_list[k]
            aim_index_loc += (((ite_x_loc, ite_y_loc, 0.0),),)

        edges_zc_gang = find_region_by_loc_tuple(aim_edges, aim_index_loc)
        self.aim_part3.Set(edges=edges_zc_gang, name='zc-gang')
            
        # zc_all集合
        self.aim_part3.Set(edges=edges_zc_c+edges_zc_gang, name='zc-all')

    def part3_surface(self):

        # <表面> -------------------------------------------------------
        aim_edges = self.aim_part3.edges

        # wall-soil_di 表面
        ite_x_loc = (self.wall_x_loc_left+self.wall_x_loc_right)*0.5
        ite_y_loc = self.qw_y_loc_down_wall

        aim_index_loc = (\
            ((ite_x_loc, ite_y_loc, 0.0),),
            )

        side1Edges = find_region_by_loc_tuple(aim_edges, aim_index_loc)
        self.aim_part3.Surface(side1Edges=side1Edges, name='wall-soil-di')

        # wall-soil-r 表面
        ite_x_loc = self.qw_x_loc_right

        aim_index_loc = ()
        for k in range(len(self.wall_index_loc_list)):
            ite_y_loc = self.wall_index_loc_list[k][1]
            aim_index_loc += (((ite_x_loc, ite_y_loc, 0.0),),)

        # <20250813>
        aim_index_loc += ((\
            (ite_x_loc, (self.qw_y_loc_down_wall+self.qw_y_loc_down)*0.5, 0.0)\
            ,),)

        side1Edges = find_region_by_loc_tuple(aim_edges, aim_index_loc)
        self.aim_part3.Surface(side1Edges=side1Edges, name='wall-soil-r')

        # wall-soil-lx 表面
        for k in range(len(self.wall_index_loc_list)):
            ite = self.wall_index_loc_list[k]
            side1Edges = aim_edges.findAt(\
                ((self.wall_x_loc_left, ite[1], 0.0), )
                )
            self.aim_part3.Surface(side1Edges=side1Edges, name='wall-soil-l{}'.format(k))

    def part3_surface_v2(self):

        # <表面> -------------------------------------------------------
        aim_edges = self.aim_part3.edges

        # 1 wall-soil_di 区域
        ite_x_loc = (self.wall_x_loc_left+self.wall_x_loc_right)*0.5
        ite_y_loc = self.qw_y_loc_down_wall

        aim_index_loc = (\
            ((ite_x_loc, ite_y_loc, 0.0),),
            )

        # wall-soil-r 区域
        for k in range(len(self.wall_index_loc_list)):
            ite_y_loc = self.wall_index_loc_list[k][1]
            aim_index_loc += (((self.qw_x_loc_right, ite_y_loc, 0.0),),)
            
        # <20251021> 底板右侧边
        aim_index_loc += (((\
            self.db_right_x, (self.db_left_y+self.db_right_y)*0.5, 0.0)
            ,),)

        # <20250813> 挡土墙延长部分(右侧)
        aim_index_loc += ((\
            (self.qw_x_loc_right, (self.qw_y_loc_down_wall+self.qw_y_loc_down)*0.5, 0.0)\
            ,),)
        
        # <20251021> 挡土墙延长部分(左侧)
        aim_index_loc += ((\
            (self.qw_x_loc_left, (self.qw_y_loc_down_wall+self.qw_y_loc_down)*0.5, 0.0)\
            ,),)
        
        # <20251021> 底板底部
        aim_index_loc += ((\
            ((self.db_left_x+self.db_right_x)*0.5, self.db_left_y, 0.0)\
            ,),)

#        # wall-soil-left 区域  || 一定是倒数两个
#        aim_index_loc += ((\
#            (self.wall_x_loc_left, self.wall_index_loc_list[-1][1], 0.0),),)
#        aim_index_loc += ((\
#            (self.wall_x_loc_left, (self.qw_y_loc_down_wall+self.qw_y_loc_down)*0.5, 0.0),),)

        aim_region = find_region_by_loc_tuple(aim_edges, aim_index_loc)
        self.aim_part3.Surface(side2Edges=aim_region, name='face')

    def assembly_process_v1(self):
        """
        assembly process
        1 chenqi 需要装配并移动到目标坐标
        2 soil 需要装配
        3 wall-zc 已经装配
        """
        def get_boundary_region_whole(aim_object):

            aim_region = aim_object.getByBoundingBox(\
                xMin=-9999.9, yMin=-9999.9, zMin=-9999.9,
                xMax=9999.9, yMax=9999.9, zMax=9999.9
                )

            return aim_region

        # chenqi
        self.tools_instance_from_part(\
            part_name=self.part1_name, instance_name="{}-1".format(self.part1_name)
            )
        self.aim_assembly.translate(\
            instanceList=("{}-1".format(self.part1_name), ), \
            vector=(self.part2_circle_x, self.part2_circle_y, 0.0)
            )

        # soil
        self.tools_instance_from_part(\
            part_name=self.part2_name, instance_name="{}-1".format(self.part2_name)
            )

        # <assembly 集合> -------------------------------------------------------------------
        instance_wall_zc = self.aim_assembly.instances['{}-1'.format(self.part3_name)]
        instance_soil = self.aim_assembly.instances['{}-1'.format(self.part2_name)]

        aim_edges_wall_zc = instance_wall_zc.edges
        aim_edges_soil = instance_soil.edges

        aim_vertices_wall_zc = instance_wall_zc.vertices
        aim_vertices_soil = instance_soil.vertices

        # 1 Set-1
        v_region1 = aim_vertices_wall_zc.getByBoundingBox(\
            xMin=0.0, yMin=self.part2_wid, zMin=0.0,
            xMax=self.part2_len, yMax=self.part2_wid, zMax=0.0
            )
        v_region2 = aim_vertices_soil.getByBoundingBox(\
            xMin=0.0, yMin=self.part2_wid, zMin=0.0,
            xMax=self.part2_len, yMax=self.part2_wid, zMax=0.0
            )

        e_region1 = aim_edges_wall_zc.getByBoundingBox(\
            xMin=0.0, yMin=self.part2_wid, zMin=0.0,
            xMax=self.part2_len, yMax=self.part2_wid, zMax=0.0
            )

        e_region2 = aim_edges_soil.getByBoundingBox(\
            xMin=0.0, yMin=self.part2_wid, zMin=0.0,
            xMax=self.part2_len, yMax=self.part2_wid, zMax=0.0
            )

        e_region3 = aim_edges_soil.getByBoundingBox(\
            xMin=0.0, yMin=self.zc_y_loc_list[1], zMin=0.0,
            xMax=0.0, yMax=self.part2_wid, zMax=0.0
            )

        region = self.aim_assembly.Set(\
            vertices=v_region1+v_region2, edges=e_region1+e_region2+e_region3, name='Set-1'
            )

        # 2 Set-1 || 全部结构
        p1_faces = self.aim_assembly.instances["{}-1".format(self.part1_name)].faces
        p2_faces = self.aim_assembly.instances["{}-1".format(self.part2_name)].faces
        p3_faces = self.aim_assembly.instances["{}-1".format(self.part3_name)].faces

        p1_edges = self.aim_assembly.instances["{}-1".format(self.part1_name)].edges
        p2_edges = self.aim_assembly.instances["{}-1".format(self.part2_name)].edges
        p3_edges = self.aim_assembly.instances["{}-1".format(self.part3_name)].edges

        p1_vertices = self.aim_assembly.instances["{}-1".format(self.part1_name)].vertices
        p2_vertices = self.aim_assembly.instances["{}-1".format(self.part2_name)].vertices
        p3_vertices = self.aim_assembly.instances["{}-1".format(self.part3_name)].vertices

        aim_f1 = get_boundary_region_whole(p1_faces)
        aim_f2 = get_boundary_region_whole(p2_faces)
        aim_f3 = get_boundary_region_whole(p3_faces)

        aim_e1 = get_boundary_region_whole(p1_edges)
        aim_e2 = get_boundary_region_whole(p2_edges)
        aim_e3 = get_boundary_region_whole(p3_edges)

        aim_v1 = get_boundary_region_whole(p1_vertices)
        aim_v2 = get_boundary_region_whole(p2_vertices)
        aim_v3 = get_boundary_region_whole(p3_vertices)

        self.aim_assembly.Set(\
            vertices=aim_v1+aim_v2+aim_v3, \
            edges=aim_e1+aim_e2+aim_e3, \
            faces=aim_f1+aim_f2+aim_f3, \
            name='Set-2'
            )

    def assembly_process_v2(self):
        """
        assembly process
        2 soil 需要装配
        3 wall-zc 已经装配
        """
        def get_boundary_region_whole(aim_object):

            aim_region = aim_object.getByBoundingBox(\
                xMin=-9999.9, yMin=-9999.9, zMin=-9999.9,
                xMax=9999.9, yMax=9999.9, zMax=9999.9
                )

            return aim_region

        # soil
        self.tools_instance_from_part(\
            part_name=self.part2_name, instance_name="{}-1".format(self.part2_name)
            )

        # <assembly 集合> -------------------------------------------------------------------
        instance_wall_zc = self.aim_assembly.instances['{}-1'.format(self.part3_name)]
        instance_soil = self.aim_assembly.instances['{}-1'.format(self.part2_name)]

        aim_edges_wall_zc = instance_wall_zc.edges
        aim_edges_soil = instance_soil.edges

        aim_vertices_wall_zc = instance_wall_zc.vertices
        aim_vertices_soil = instance_soil.vertices

        # 1 Set-1
        v_region1 = aim_vertices_wall_zc.getByBoundingBox(\
            xMin=0.0, yMin=self.part2_wid, zMin=0.0,
            xMax=self.part2_len, yMax=self.part2_wid, zMax=0.0
            )
        v_region2 = aim_vertices_soil.getByBoundingBox(\
            xMin=0.0, yMin=self.part2_wid, zMin=0.0,
            xMax=self.part2_len, yMax=self.part2_wid, zMax=0.0
            )

        e_region1 = aim_edges_wall_zc.getByBoundingBox(\
            xMin=0.0, yMin=self.part2_wid, zMin=0.0,
            xMax=self.part2_len, yMax=self.part2_wid, zMax=0.0
            )

        e_region2 = aim_edges_soil.getByBoundingBox(\
            xMin=0.0, yMin=self.part2_wid, zMin=0.0,
            xMax=self.part2_len, yMax=self.part2_wid, zMax=0.0
            )

        e_region3 = aim_edges_soil.getByBoundingBox(\
            xMin=0.0, yMin=self.zc_y_loc_list[1], zMin=0.0,
            xMax=0.0, yMax=self.part2_wid, zMax=0.0
            )

        region = self.aim_assembly.Set(\
            vertices=v_region1+v_region2, edges=e_region1+e_region2+e_region3, name='Set-1'
            )

        # 2 Set-1 || 全部结构
        p2_faces = self.aim_assembly.instances["{}-1".format(self.part2_name)].faces
        p3_faces = self.aim_assembly.instances["{}-1".format(self.part3_name)].faces

        p2_edges = self.aim_assembly.instances["{}-1".format(self.part2_name)].edges
        p3_edges = self.aim_assembly.instances["{}-1".format(self.part3_name)].edges

        p2_vertices = self.aim_assembly.instances["{}-1".format(self.part2_name)].vertices
        p3_vertices = self.aim_assembly.instances["{}-1".format(self.part3_name)].vertices

        aim_f2 = get_boundary_region_whole(p2_faces)
        aim_f3 = get_boundary_region_whole(p3_faces)

        aim_e2 = get_boundary_region_whole(p2_edges)
        aim_e3 = get_boundary_region_whole(p3_edges)

        aim_v2 = get_boundary_region_whole(p2_vertices)
        aim_v3 = get_boundary_region_whole(p3_vertices)

        self.aim_assembly.Set(\
            vertices=aim_v2+aim_v3, \
            edges=aim_e2+aim_e3, \
            faces=aim_f2+aim_f3, \
            name='Set-2'
            )

    def step_process(self):
        """
        step process || 各项参数依据用户提供的模板model文件
        """
        # 地应力平衡分析步
        self.aim_model.GeostaticStep(name='geo', previous='Initial',
            timeIncrementationMethod=AUTOMATIC, initialInc=0.1, minInc=1e-05,
            maxInc=1.0, utol=1e-05, nlgeom=ON)
        self.aim_model.steps['geo'].setValues(maxNumInc=10000)

        # add-wall分析步
        self.aim_model.SoilsStep(name='add-wall', previous='geo',
            response=STEADY_STATE, creep=OFF, initialInc=0.1, end=None, utol=None,
            cetol=None, amplitude=RAMP, matrixSolver=DIRECT, matrixStorage=UNSYMMETRIC)
        self.aim_model.steps['add-wall'].setValues(maxNumInc=10000)

        # wa分析步
        wall_name = 'add-wall'
        for k in range(len(self.wall_index_loc_list)):
            wall_name = 'wa{}'.format(k)
            if k==0:
                self.aim_model.SoilsStep(name=wall_name, previous='add-wall',
                    response=STEADY_STATE, creep=OFF, initialInc=0.1, end=None, utol=None,
                    cetol=None, amplitude=RAMP, matrixSolver=DIRECT, matrixStorage=UNSYMMETRIC)
            else:
                self.aim_model.SoilsStep(name=wall_name, previous='wa{}'.format(k-1),
                    response=STEADY_STATE, creep=OFF, initialInc=0.1, end=None, utol=None,
                    cetol=None, amplitude=RAMP, matrixSolver=DIRECT, matrixStorage=UNSYMMETRIC)
            self.aim_model.steps[wall_name].setValues(maxNumInc=10000)

        # add-zjnt分析步
        self.aim_model.SoilsStep(name='add-zjnt', previous=wall_name,
            response=STEADY_STATE, creep=OFF, initialInc=0.1, end=None, utol=None,
            cetol=None, amplitude=RAMP, matrixSolver=DIRECT, matrixStorage=UNSYMMETRIC)

    def  mesh_node_set(self):
        """
        注意：必须和step_process对应
        """

        def create_tunnel_hist_out_set(aim_object, set_name, x_loc, y_loc):

            nodes = aim_object.getClosest(coordinates=(\
                (x_loc, y_loc, 0.0)
                ))
            node_id = nodes.label
            aim_node = aim_object.sequenceFromLabels((node_id,))
            self.aim_part1.Set(nodes=aim_node, name=set_name)
            self.tunnel_hist_set_name_list.append(set_name)

        def create_zjnt_hist_out_set(aim_object, set_name, x_loc, y_loc):
            
            nodes = aim_object.getClosest(coordinates=(\
                (x_loc, y_loc, 0.0)
                ))
            node_id = nodes.label
            aim_node = aim_object.sequenceFromLabels((node_id,))
            self.aim_part2.Set(nodes=aim_node, name=set_name)
            self.zjnt_hist_set_name_list.append(set_name)

        def create_wall_hist_out_set(aim_object, set_name, x_loc, y_loc):

            nodes = aim_object.getClosest(coordinates=(\
                (x_loc, y_loc, 0.0)
                ))
            node_id = nodes.label
            aim_node = aim_object.sequenceFromLabels((node_id,))
            self.aim_part3.Set(nodes=aim_node, name=set_name)
            self.wall_hist_set_name_lits.append(set_name)

        def create_GS_hist_out_set(aim_object, set_name, x_loc, y_loc):
            
            nodes = aim_object.getClosest(coordinates=(\
                (x_loc, y_loc, 0.0)
                ))
            node_id = nodes.label
            aim_node = aim_object.sequenceFromLabels((node_id,))
            self.aim_part2.Set(nodes=aim_node, name=set_name)
            self.GS_hist_set_name_list.append(set_name)

        def create_EB_hist_out_set(aim_object, set_name, x_loc, y_loc):
            
            nodes = aim_object.getClosest(coordinates=(\
                (x_loc, y_loc, 0.0)
                ))
            node_id = nodes.label
            aim_node = aim_object.sequenceFromLabels((node_id,))
            self.aim_part2.Set(nodes=aim_node, name=set_name)
            self.EB_hist_set_name_list.append(set_name)

        def create_MJ_hist_out_set(aim_object, set_name, xMin, yMin, xMax, yMax):
            
            nodes = aim_object.getByBoundingBox(
                xMin=xMin,
                yMin=yMin,
                zMin=0.0,
                xMax=xMax,
                yMax=yMax,
                zMax=0.0
                )
            
            # node id list
            node_id_list = []
            for ite in nodes:
                node_id = int(ite.label)
                f_set_name = "{A}{B}".format(A=set_name, B=node_id)
                # create set
                aim_node = aim_object.sequenceFromLabels((node_id,))
                self.aim_part2.Set(nodes=aim_node, name=f_set_name)
                self.MJ_hist_set_name_list.append(f_set_name)

        def create_MJ_hist_out_set_v2(aim_object, set_name, xMin, yMin, xMax, yMax):
            
            nodes = aim_object.getByBoundingBox(
                xMin=xMin,
                yMin=yMin,
                zMin=0.0,
                xMax=xMax,
                yMax=yMax,
                zMax=0.0
                )
            
            f_set_name = "{A}".format(A=set_name)
            # create set
            self.aim_part2.Set(nodes=nodes, name=f_set_name)
            self.MJ_hist_set_name_list.append(f_set_name)

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # 1 隧道 (间隔45°顺时针)
        aim_nodes = self.aim_part1.nodes

        # 1.1 顶部
        set_name = 'Tunnel_1_top'
        top_x = self.part2_circle_x
        top_y = self.part2_circle_y+self.part2_circle_ratio
        create_tunnel_hist_out_set(aim_nodes, set_name, top_x, top_y)

        # 1.2 右上45°
        set_name = 'Tunnel_2_top_right45'
        temp_var_45 = self.part2_circle_ratio*math.sin(math.radians(45))
        temp_x = self.part2_circle_x + temp_var_45
        temp_y = self.part2_circle_y + temp_var_45
        create_tunnel_hist_out_set(aim_nodes, set_name, temp_x, temp_y)

        # 1.3 右侧
        set_name = 'Tunnel_3_right'
        right_x = self.part2_circle_x+self.part2_circle_ratio
        right_y = self.part2_circle_y
        create_tunnel_hist_out_set(aim_nodes, set_name, right_x, right_y)

        # 1.4 右下45°
        set_name = 'Tunnel_4_right_bottom45'
        temp_x = self.part2_circle_x + temp_var_45
        temp_y = self.part2_circle_y - temp_var_45
        create_tunnel_hist_out_set(aim_nodes, set_name, temp_x, temp_y)

        # 1.5 底部
        set_name = 'Tunnel_5_bottom'
        bottom_x = self.part2_circle_x
        bottom_y = self.part2_circle_y-self.part2_circle_ratio
        create_tunnel_hist_out_set(aim_nodes, set_name, bottom_x, bottom_y)

        # 1.6 左下45°
        set_name = 'Tunnel_6_bottom_left45'
        temp_x = self.part2_circle_x - temp_var_45
        temp_y = self.part2_circle_y - temp_var_45
        create_tunnel_hist_out_set(aim_nodes, set_name, temp_x, temp_y)

        # 1.7 左侧
        set_name = 'Tunnel_7_left'
        left_x = self.part2_circle_x-self.part2_circle_ratio
        left_y = self.part2_circle_y
        create_tunnel_hist_out_set(aim_nodes, set_name, left_x, left_y)

        # 1.8 左上45°
        set_name = 'Tunnel_8_left_up45'
        temp_x = self.part2_circle_x - temp_var_45
        temp_y = self.part2_circle_y + temp_var_45
        create_tunnel_hist_out_set(aim_nodes, set_name, temp_x, temp_y)

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # 2 注浆囊体 （四周6个顶点）
        aim_nodes = self.aim_part2.nodes

        xll = self.sjnt_x_loc_left
        xlr = self.sjnt_x_loc_right
        ylu = self.sjnt_y_loc_up
        yld = self.sjnt_y_loc_down

        # 左上
        create_zjnt_hist_out_set(aim_nodes, 'zjnt_hist_left_up', xll, ylu)
        # 左中
        create_zjnt_hist_out_set(aim_nodes, 'zjnt_hist_left_mid', xll, (ylu+yld)*0.5)
        # 左下
        create_zjnt_hist_out_set(aim_nodes, 'zjnt_hist_left_down', xll, yld)
        # 右上
        create_zjnt_hist_out_set(aim_nodes, 'zjnt_hist_right_up', xlr, ylu)
        # 右中
        create_zjnt_hist_out_set(aim_nodes, 'zjnt_hist_right_mid', xlr, (ylu+yld)*0.5)
        # 右下
        create_zjnt_hist_out_set(aim_nodes, 'zjnt_hist_right_down', xlr, yld)

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # 3 挡土墙 （从上往下，间隔2m取1个点）
        aim_nodes = self.aim_part3.nodes
        
        find_loc_x = self.qw_x_loc_left  # 默认墙的左侧
        find_loc_y = self.qw_y_loc_up
        search_gap = 2  # 搜寻间隔2m，应当为整数
        index_loc = 0  # 用于创建集合名称

        while find_loc_y > self.qw_y_loc_down_wall:  # 搜寻区域一直延伸到底部
            
            create_wall_hist_out_set(\
                aim_nodes, 'wall_Y_{}m'.format(int(index_loc)), find_loc_x, find_loc_y
                )

            find_loc_y -= search_gap
            index_loc += search_gap

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # 4 地表 （从挡土墙后，沿地表，间隔2米设置）
        aim_nodes = self.aim_part2.nodes

        find_loc_x = self.qw_x_loc_right  # 默认墙的右侧开始
        find_loc_y = self.qw_y_loc_up
        search_gap = 2  # 搜寻间隔2m，应当为整数
        index_loc = 0  # 用于创建集合名称

        while find_loc_x < self.part2_len:  # 搜寻区域不能超过模型
            
            create_GS_hist_out_set(\
                aim_nodes, 'GS_X+{}m'.format(int(index_loc)), find_loc_x, find_loc_y
                )

            find_loc_x += search_gap
            index_loc += search_gap

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # 5 基坑底部 （从挡土墙前，沿基坑开挖面，间隔2米设置）
        aim_nodes = self.aim_part2.nodes

        find_loc_x = self.qw_x_loc_left  # 默认墙的左侧开始
        find_loc_y = self.qw_y_loc_down  # 基坑的底部
        search_gap = 2  # 搜寻间隔2m，应当为整数
        index_loc = 0  # 用于创建集合名称

        while find_loc_x > 0.0:  # 搜寻区域不能超过模型
            
            create_EB_hist_out_set(\
                aim_nodes, 'EB_X+{}m'.format(int(index_loc)), find_loc_x, find_loc_y
                )

            find_loc_x -= search_gap
            index_loc += search_gap

#        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#        # 6 密集监测区 - 挡土墙和隧道临近的矩形区域 （v1::按照单元输出版本）
#        aim_nodes = self.aim_part2.elements
#
#        xMin_loc = self.qw_x_loc_right  # 默认挡土墙右侧，作为左边界
#        xMax_loc = self.suidao_right_line_x_loc
#        yMin_loc = self.suidao_right_line_y_loc_bottom
#        yMax_loc = self.suidao_right_line_y_loc_top
#
#        create_MJ_hist_out_set(aim_nodes, "MJ-SD-ID", xMin_loc, yMin_loc, xMax_loc, yMax_loc)
#
#        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#        # 7 密集监测区 - 地表向下2米，宽度同上 （v1::按照单元输出版本）
#        aim_nodes = self.aim_part2.elements
#
#        xMin_loc = self.qw_x_loc_right  # 默认挡土墙右侧，作为左边界
#        xMax_loc = self.suidao_right_line_x_loc
#        yMin_loc = self.part2_wid-2.0
#        yMax_loc = self.part2_wid
#
#        create_MJ_hist_out_set(aim_nodes, "MJ-DB-ID", xMin_loc, yMin_loc, xMax_loc, yMax_loc)

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # 6 密集监测区 - 挡土墙和隧道临近的矩形区域 （v2::按照节点输出版本）
        aim_nodes = self.aim_part2.nodes

        xMin_loc = self.qw_x_loc_right  # 默认挡土墙右侧，作为左边界
        xMax_loc = self.suidao_right_line_x_loc
        yMin_loc = self.suidao_right_line_y_loc_bottom
        yMax_loc = self.suidao_right_line_y_loc_top

        create_MJ_hist_out_set(aim_nodes, "MJ-SD", xMin_loc, yMin_loc, xMax_loc, yMax_loc)

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # 7 密集监测区 - 地表向下2米，宽度同上 （v2::按照节点输出版本）
        aim_nodes = self.aim_part2.nodes

        xMin_loc = self.qw_x_loc_right  # 默认挡土墙右侧，作为左边界
        xMax_loc = self.suidao_right_line_x_loc
        yMin_loc = self.part2_wid-2.0
        yMax_loc = self.part2_wid

        create_MJ_hist_out_set(aim_nodes, "MJ-DB", xMin_loc, yMin_loc, xMax_loc, yMax_loc)

    def step_process_v2(self, step_zjnt_maxNumInc, step_zjnt_minInc):
        """
        step process || 各项参数依据用户提供的模板model文件
        """
        def create_hist_set(part_name, hist_name, set_name, var_tuple):
            regionDef=self.aim_assembly.allInstances["{}-1".format(part_name)].sets[set_name]
            self.aim_model.HistoryOutputRequest(name=hist_name, 
                createStepName='geo', variables=var_tuple, region=regionDef, 
                sectionPoints=DEFAULT, rebar=EXCLUDE)

        # 1 地应力平衡分析步 , nlgeom=ON
        self.aim_model.GeostaticStep(name='geo', previous='Initial', maxNumInc=10000, 
            timeIncrementationMethod=AUTOMATIC, initialInc=1, minInc=1e-05,
            maxInc=1.0, utol=1e-05, nlgeom=OFF)
        self.aim_model.steps['geo'].setValues(matrixSolver=DIRECT, 
            matrixStorage=UNSYMMETRIC)

        # 2 开挖分析步
        self.aim_model.StaticStep(name='kw', previous='geo', maxNumInc=100000,
            initialInc=0.2, minInc=1e-05, maxInc=1.0, nlgeom=OFF)
        self.aim_model.steps['kw'].setValues(matrixSolver=DIRECT, 
            matrixStorage=UNSYMMETRIC)

        # 2 注浆囊体分析步
        self.aim_model.StaticStep(name='zjnt', previous='kw', maxNumInc=step_zjnt_maxNumInc,
            initialInc=0.2, minInc=step_zjnt_minInc, maxInc=1.0, nlgeom=OFF)
        self.aim_model.steps['zjnt'].setValues(matrixSolver=DIRECT, 
            matrixStorage=UNSYMMETRIC)

        # 设置场变量
#        self.aim_model.fieldOutputRequests['F-Output-1'].setValues(
#            variables=('S', 'LE', 'U', 'V', 'POR', 'RF', 'EVOL'))
        self.aim_model.fieldOutputRequests['F-Output-1'].setValues(
            variables=('U', 'CDISP', 'CF', 'CSTRESS', 'LE', 'POR', 'RF', 'S', 'SAT', 'VOIDR', ))

#        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#        # 设置历程输出
#        # 1 隧道
#        for ite in self.tunnel_hist_set_name_list:
#            create_hist_set(self.part2_name, hist_name=ite, set_name=ite, \
#            var_tuple=('U1', 'U2', 'V1', 'V2', 'RF1', 'RF2'))
#
#        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#        # 2 注浆囊体四周
#        for ite in self.zjnt_hist_set_name_list:
#            create_hist_set(self.part2_name, hist_name=ite, set_name=ite, \
#            var_tuple=('U1', 'U2', 'V1', 'V2', 'RF1', 'RF2'))
#
#        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#        # 3 挡土墙竖向
#        for ite in self.wall_hist_set_name_lits:
#            create_hist_set(self.part3_name, hist_name=ite, set_name=ite, \
#            var_tuple=('U1', 'U2', 'V1', 'V2', 'RF1', 'RF2'))
#
#        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#        # 4 GS
#        for ite in self.GS_hist_set_name_list:
#            create_hist_set(self.part2_name, hist_name=ite, set_name=ite, \
#            var_tuple=('U1', 'U2', 'V1', 'V2', 'RF1', 'RF2'))
#
#        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#        # 5 EB
#        for ite in self.EB_hist_set_name_list:
#            create_hist_set(self.part2_name, hist_name=ite, set_name=ite, \
#            var_tuple=('U1', 'U2', 'V1', 'V2', 'RF1', 'RF2'))
#
#        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#        # 6 MJ
##        for ite in self.MJ_hist_set_name_list:
##            create_hist_set(self.part2_name, hist_name=ite, set_name=ite, \
##            var_tuple=('S11', 'S22', 'S12', 'E11', 'E22', 'E12', 'PE11', 'PE22', 
##            'PE12', 'LE11', 'LE22', 'LE12', 'POR'))
#
#        for ite in self.MJ_hist_set_name_list:
#            create_hist_set(self.part2_name, hist_name=ite, set_name=ite, \
#            var_tuple=('U1', 'U2', 'V1', 'V2', 'RF1', 'RF2'))

    def interaction_process(self):
        """
        interaction process
        """
        # create interaction para
        aim_contact = self.aim_model.ContactProperty('Int-1')

        aim_contact.TangentialBehavior(
            formulation=PENALTY, directionality=ISOTROPIC, slipRateDependency=OFF,
            pressureDependency=OFF, temperatureDependency=OFF, dependencies=0,
            table=((0.35, ), ), shearStressLimit=None, maximumElasticSlip=FRACTION,
            fraction=0.005, elasticSlipStiffness=None
            )

        aim_contact.NormalBehavior(
            pressureOverclosure=HARD, allowSeparation=ON,
            constraintEnforcementMethod=DEFAULT
            )

        # create interaction pair
        # 1 chenqi
        # <part1处理>
        region = self.aim_assembly.instances[\
            '{}-1'.format(self.part1_name)
            ].sets['cq-all']

        self.aim_model.ModelChange(name='chenqi',
            createStepName='geo', region=region, activeInStep=False,
            includeStrain=False)

        self.aim_model.interactions['chenqi'].setValuesInStep(
            stepName='add-wall', activeInStep=True)

        # <part2处理>
        region = self.aim_assembly.instances[\
            '{}-1'.format(self.part2_name)
            ].sets['soil-cq']

        self.aim_model.ModelChange(name='chenqi_del',
            createStepName='geo', region=region, activeInStep=False,
            includeStrain=False)

        # <chenqi在part1和part2之间的接触>
        region1=self.aim_assembly.instances[\
            '{}-1'.format(self.part1_name)
            ].surfaces['cq-soil']

        region2=self.aim_assembly.instances[\
            '{}-1'.format(self.part2_name)
            ].surfaces['soil-chenqi']

        self.aim_model.SurfaceToSurfaceContactStd(
            name='chenqi_contact', createStepName='add-wall', \
            master=region1, slave=region2, sliding=FINITE, thickness=ON,
            interactionProperty='Int-1', adjustMethod=NONE, \
            initialClearance=OMIT, datumAxis=None, clearanceRegion=None)

        # 2 soil-qw
        region = self.aim_assembly.instances[\
            '{}-1'.format(self.part2_name)
            ].sets['soil-qw']

        self.aim_model.ModelChange(name='soil-qw',
            createStepName='add-wall', region=region, activeInStep=False,
            includeStrain=False)

        # 3 soil
        for k in range(len(self.wall_index_loc_list)):

            region = self.aim_assembly.instances[\
                '{}-1'.format(self.part2_name)
                ].sets['wall-{}'.format(k)]

            self.aim_model.ModelChange(name='soil{}'.format(k),
                createStepName='wa{}'.format(k), region=region, activeInStep=False,
                includeStrain=False)

        # 4 wall
        region = self.aim_assembly.instances[\
            '{}-1'.format(self.part3_name)
            ].sets['wall-all']

        self.aim_model.ModelChange(name='wall',
            createStepName='geo', region=region, activeInStep=False,
            includeStrain=False)

        self.aim_model.interactions['wall'].setValuesInStep(
            stepName='add-wall', activeInStep=True)

        # 5 wall-soil-do
        region1 = self.aim_assembly.instances[\
            '{}-1'.format(self.part3_name)
            ].surfaces['wall-soil-di']

        region2 = self.aim_assembly.instances[\
            '{}-1'.format(self.part2_name)
            ].surfaces['soil-wall-di']

        self.aim_model.SurfaceToSurfaceContactStd(
            name='wall-soil-di', createStepName='add-wall', master=region1,
            slave=region2, sliding=FINITE, thickness=ON,
            interactionProperty='Int-1', adjustMethod=NONE,
            initialClearance=OMIT, datumAxis=None, clearanceRegion=None
            )

        # 6 wall-soil-l
        for k in range(len(self.wall_index_loc_list)):

            region1 = self.aim_assembly.instances[\
                '{}-1'.format(self.part3_name)
                ].surfaces['wall-soil-l{}'.format(k)]

            region2 = self.aim_assembly.instances[\
                '{}-1'.format(self.part2_name)
                ].surfaces['soil-wall-l{}'.format(k)]

            self.aim_model.SurfaceToSurfaceContactStd(
                name='wall-soil-l{}'.format(k), createStepName='add-wall',
                master=region1, slave=region2, sliding=FINITE, thickness=ON,
                interactionProperty='Int-1', adjustMethod=NONE, initialClearance=OMIT,
                datumAxis=None, clearanceRegion=None)

            self.aim_model.interactions[\
                'wall-soil-l{}'.format(k)
                ].deactivate('wa{}'.format(k))

        # 7 wall-soil-r
        region1 = self.aim_assembly.instances[\
                '{}-1'.format(self.part3_name)
                ].surfaces['wall-soil-r']

        region2 = self.aim_assembly.instances[\
                '{}-1'.format(self.part2_name)
                ].surfaces['soil-wall-r']

        self.aim_model.SurfaceToSurfaceContactStd(
            name='wall-soil-r', createStepName='add-wall',
            master=region1, slave=region2, sliding=FINITE, thickness=ON,
            interactionProperty='Int-1', adjustMethod=NONE, initialClearance=OMIT,
            datumAxis=None, clearanceRegion=None)

        # 8 zc
        for k in range(len(self.wall_index_loc_list)):

            region = self.aim_assembly.instances[\
                '{}-1'.format(self.part3_name)
                ].sets['zc{}'.format(k)]

            self.aim_model.ModelChange(
                name='zc{}'.format(k), createStepName='geo', region=region,
                activeInStep=False, includeStrain=False
                )

            self.aim_model.interactions['zc{}'.format(k)].setValuesInStep(
                stepName='wa{}'.format(k), activeInStep=True
                )

    def interaction_process_v2(self):
        """
        interaction process
        """
        # 1 Int-1
        region = self.aim_assembly.instances[\
            '{}-1'.format(self.part3_name)].sets['wall-all']

        self.aim_model.ModelChange(\
            name='Int-1', createStepName='geo', region=region, activeInStep=False, 
            includeStrain=False
            )
        self.aim_model.interactions['Int-1'].setValuesInStep(\
            stepName='kw', activeInStep=True
            )
            
        # 2 Int-2
        region = self.aim_assembly.instances[\
            '{}-1'.format(self.part1_name)].sets['cq-all']

        self.aim_model.ModelChange(\
            name='Int-2', createStepName='geo', region=region, activeInStep=False, 
            includeStrain=False
            )
        self.aim_model.interactions['Int-2'].setValuesInStep(\
            stepName='kw', activeInStep=True
            )

        # 3 Int-3
        region = self.aim_assembly.instances[\
            '{}-1'.format(self.part2_name)].sets['soil-qw']

        self.aim_model.ModelChange(\
            name='Int-3', createStepName='kw', region=region, activeInStep=False, 
            includeStrain=False
            )
        
        # 4 constrain-1
        region1 = self.aim_assembly.instances[\
            '{}-1'.format(self.part2_name)].surfaces['wall-soil']
        region2 = self.aim_assembly.instances[\
            '{}-1'.format(self.part3_name)].surfaces['face']

        self.aim_model.Tie(name='Constraint-1', master=region1, slave=region2, 
            positionToleranceMethod=COMPUTED, adjust=OFF, tieRotations=ON, 
            thickness=ON)
        
        # 5 constrain-2
        region1 = self.aim_assembly.instances[\
            '{}-1'.format(self.part2_name)].surfaces['soil-chenqi']
        region2 = self.aim_assembly.instances[\
            '{}-1'.format(self.part1_name)].surfaces['cq-soil']

        self.aim_model.Tie(name='Constraint-2', master=region1, slave=region2, 
            positionToleranceMethod=COMPUTED, adjust=OFF, tieRotations=ON, 
            thickness=ON)

    def material_and_section_process(self, soil_E=30000000000.0, soil_fai=10.0, soil_c=50000.0):

        # 1 create material
        # 1.1 gang
        material_gang = self.aim_model.Material(name='gang')

        material_gang.Density(\
            table=((7850.0, ), )
            )
        material_gang.Elastic(\
            table=((210000000000.0, 0.3), )
            )

        # 1.2 hunningtu
        material_hunningtu = self.aim_model.Material(name='hunningtu')

        material_hunningtu.Density(\
            table=((2500.0, ), )
            )
        material_hunningtu.Elastic(\
            table=((30000000000.0, 0.2), )
            )
        material_hunningtu.Permeability(\
            specificWeight=10000.0, inertialDragCoefficient=0.142887, \
            table=((1e-12, 0.3), )
            )

        # 1.3 soil
        material_soil = self.aim_model.Material(name='soil')

        material_soil.Density(\
            table=((1800.0, ), )
            )
        material_soil.Elastic(dependencies=1, \
            table=((soil_E, 0.49, 1.0), (200000000.0, 0.2, 2.0))
            )
        material_soil.Permeability(\
            specificWeight=10000.0, inertialDragCoefficient=0.142887,
            table=((1e-8, 0.9), )
            )
        material_soil.MohrCoulombPlasticity(dependencies=1, \
            table=((soil_fai, 0.1, 1.0), (30.0, 0.1, 2.0))
            )
        material_soil.mohrCoulombPlasticity.MohrCoulombHardening(\
            dependencies=1, table=((soil_c, 0.0, 1.0), (14300000.0, 0.0, 2.0))
            )
        material_soil.mohrCoulombPlasticity.TensionCutOff(
            temperatureDependency=OFF, dependencies=0, table=((0.0, 0.0), )
            )

        # 1.4 zjnt
        material_zjnt = self.aim_model.Material(name='zjnt')
        material_zjnt.Density(\
            table=((1800.0, ), )
            )
        material_zjnt.Elastic(\
            table=((200000000.0, 0.2), )
            )

        # 2 create section
        # 2.1 chenqi
        self.aim_model.HomogeneousSolidSection(\
            name='chenqi', material='hunningtu', thickness=None
            )

        # 2.2 gang
        self.aim_model.PipeProfile(\
            name='Profile-1', r=0.4, t=0.05
            )
        self.aim_model.BeamSection(name='gang',
            integration=DURING_ANALYSIS, poissonRatio=0.0, profile='Profile-1',
            material='gang', temperatureVar=LINEAR, consistentMassMatrix=False
            )

        # 2.3 gj-hnt
        self.aim_model.RectangularProfile(\
            name='Profile-2', a=1.4, b=1.4
            )
        self.aim_model.BeamSection(name='gj-hnt',
            integration=DURING_ANALYSIS, poissonRatio=0.0, profile='Profile-2',
            material='hunningtu', temperatureVar=LINEAR, consistentMassMatrix=False
            )

        # 2.4 soil
        self.aim_model.HomogeneousSolidSection(\
            name='soil', material='soil', thickness=None
            )

        # 2.5 wall
        self.aim_model.HomogeneousSolidSection(\
            name='wall', material='hunningtu', thickness=None
            )

        # 2.6 zjnt
        self.aim_model.HomogeneousSolidSection(\
            name='zjnt', material='zjnt', thickness=None
            )

        # 3 sction process
        # 3.1 part chenqi
        aim_region = self.aim_part1.sets['cq-all']
        self.aim_part1.SectionAssignment(\
            region=aim_region, sectionName='chenqi', offset=0.0, offsetType=MIDDLE_SURFACE,
            offsetField='', thicknessAssignment=FROM_SECTION
            )

        # 3.2 soil
        aim_region = self.aim_part2.sets['soil']
        self.aim_part2.SectionAssignment(\
            region=aim_region, sectionName='soil', offset=0.0, offsetType=MIDDLE_SURFACE,
            offsetField='', thicknessAssignment=FROM_SECTION
            )

        aim_region = self.aim_part2.sets['soil-cq']
        self.aim_part2.SectionAssignment(\
            region=aim_region, sectionName='chenqi', offset=0.0, offsetType=MIDDLE_SURFACE,
            offsetField='', thicknessAssignment=FROM_SECTION
            )

        aim_region = self.aim_part2.sets['sjnt']
        self.aim_part2.SectionAssignment(\
            region=aim_region, sectionName='zjnt', offset=0.0, offsetType=MIDDLE_SURFACE,
            offsetField='', thicknessAssignment=FROM_SECTION
            )

        # 3.3 wall-zc
        aim_region = self.aim_part3.sets['wall-all']
        self.aim_part3.SectionAssignment(\
            region=aim_region, sectionName='wall', offset=0.0, offsetType=MIDDLE_SURFACE,
            offsetField='', thicknessAssignment=FROM_SECTION
            )

        for k in range(len(self.zc_y_loc_list)):
            if k==0:
                aim_region = self.aim_part3.sets['zc{}'.format(k)]
                self.aim_part3.SectionAssignment(region=aim_region, sectionName='gj-hnt', offset=0.0,
                    offsetType=MIDDLE_SURFACE, offsetField='',
                    thicknessAssignment=FROM_SECTION)
            else:
                aim_region = self.aim_part3.sets['zc{}'.format(k)]
                self.aim_part3.SectionAssignment(region=aim_region, sectionName='gang', offset=0.0,
                    offsetType=MIDDLE_SURFACE, offsetField='',
                    thicknessAssignment=FROM_SECTION)
        
        # 3.4 设置wall-zc的梁截面方向
        region=self.aim_part3.sets['za-all']
        self.aim_part3.assignBeamSectionOrientation(\
            region=region, method=N1_COSINES, n1=(0.0, 0.0, -1.0)
            )

    def material_and_section_process_v2(self, soil_E=30000000.0, soil_fai=10.0, soil_c=50000.0, soil_density=1800.0,
        soil_xmu=0.49, soil_2_E=10000000.0):

        # 1 create material
        # 1.1 gang
        material_gang = self.aim_model.Material(name='gang')

        material_gang.Density(\
            table=((7850.0, ), )
            )
        material_gang.Elastic(\
            table=((210000000000.0, 0.3), )
            )

        # 1.2 hunningtu
        material_hunningtu = self.aim_model.Material(name='hunningtu')

        material_hunningtu.Density(\
            table=((2500.0, ), )
            )
        material_hunningtu.Elastic(\
            table=((20000000000.0, 0.2), )
            )

        # 1.3 soil-1
        material_soil_1 = self.aim_model.Material(name='soil-1')

        material_soil_1.Density(\
            table=((soil_density, ), )
            )
        material_soil_1.Elastic(dependencies=1, \
            table=((soil_E, soil_xmu, 1.0), (2000.0, 0.2, 2.0))
            )
        material_soil_1.MohrCoulombPlasticity(dependencies=1, \
            table=((soil_fai, 0.1, 1.0), (30.0, 0.1, 2.0))
            )
        material_soil_1.mohrCoulombPlasticity.MohrCoulombHardening(\
            dependencies=0, table=((soil_c, 0.0), )
            )
        material_soil_1.mohrCoulombPlasticity.TensionCutOff(
            temperatureDependency=OFF, dependencies=0, table=((0.0, 0.0), )
            )
        
        # 1.3 soil-2  || 底部土体用固定参数
        material_soil_2 = self.aim_model.Material(name='soil-2')

        material_soil_2.Density(\
            table=((soil_density, ), )
            )
        material_soil_2.Elastic(\
            table=((soil_2_E, 0.2), )
            )

#        # 1.4 zjnt
#        material_zjnt = self.aim_model.Material(name='zjnt')
#        material_zjnt.Density(\
#            table=((1800.0, ), )
#            )
#        material_zjnt.Elastic(\
#            table=((2000.0, 0.2), )
#            )
        
        # 1.5 diban
        material_diban = self.aim_model.Material(name='diban')
        material_diban.Density(\
            table=((2500.0, ), )
            )
        material_diban.Elastic(\
            table=((2000000000000.0, 0.2), )
            )

        # 2 create section
        # 2.1 chenqi
        self.aim_model.HomogeneousSolidSection(\
            name='chenqi', material='hunningtu', thickness=None
            )

        # 2.2 gang
        self.aim_model.PipeProfile(\
            name='Profile-1', r=0.4, t=0.05
            )
        self.aim_model.BeamSection(name='gang',
            integration=DURING_ANALYSIS, poissonRatio=0.0, profile='Profile-1',
            material='gang', temperatureVar=LINEAR, consistentMassMatrix=False
            )

        # 2.3 gj-hnt
        self.aim_model.RectangularProfile(\
            name='Profile-2', a=1.4, b=1.4
            )
        self.aim_model.BeamSection(name='gj-hnt',
            integration=DURING_ANALYSIS, poissonRatio=0.0, profile='Profile-2',
            material='hunningtu', temperatureVar=LINEAR, consistentMassMatrix=False
            )

        # 2.4 soil-1
        self.aim_model.HomogeneousSolidSection(\
            name='soil-1', material='soil-1', thickness=None
            )
            
        # 2.4 soil-2
        self.aim_model.HomogeneousSolidSection(\
            name='soil-2', material='soil-2', thickness=None
            )

        # 2.5 wall
        self.aim_model.HomogeneousSolidSection(\
            name='wall', material='hunningtu', thickness=None
            )

#        # 2.6 zjnt
#        self.aim_model.HomogeneousSolidSection(\
#            name='zjnt', material='zjnt', thickness=None
#            )
        
        # 2.7 diban
        self.aim_model.HomogeneousSolidSection(\
            name='diban', material='diban', thickness=None
            )

        # 3 sction process
        # 3.1 part chenqi
        aim_region = self.aim_part1.sets['cq-all']
        self.aim_part1.SectionAssignment(\
            region=aim_region, sectionName='chenqi', offset=0.0, offsetType=MIDDLE_SURFACE,
            offsetField='', thicknessAssignment=FROM_SECTION
            )

        # 3.2 soil-1
        aim_region = self.aim_part2.sets['soil-1']
        self.aim_part2.SectionAssignment(\
            region=aim_region, sectionName='soil-1', offset=0.0, offsetType=MIDDLE_SURFACE,
            offsetField='', thicknessAssignment=FROM_SECTION
            )
            
        # 3.2 soil-2
        aim_region = self.aim_part2.sets['soil-2']
        self.aim_part2.SectionAssignment(\
            region=aim_region, sectionName='soil-2', offset=0.0, offsetType=MIDDLE_SURFACE,
            offsetField='', thicknessAssignment=FROM_SECTION
            )

#        aim_region = self.aim_part2.sets['soil-cq']
#        self.aim_part2.SectionAssignment(\
#            region=aim_region, sectionName='chenqi', offset=0.0, offsetType=MIDDLE_SURFACE,
#            offsetField='', thicknessAssignment=FROM_SECTION
#            )

        aim_region = self.aim_part2.sets['sjnt']
        self.aim_part2.SectionAssignment(\
            region=aim_region, sectionName='soil-1', offset=0.0, offsetType=MIDDLE_SURFACE,
            offsetField='', thicknessAssignment=FROM_SECTION
            )

        # 3.3 wall-zc
        aim_region = self.aim_part3.sets['wall']
        self.aim_part3.SectionAssignment(\
            region=aim_region, sectionName='wall', offset=0.0, offsetType=MIDDLE_SURFACE,
            offsetField='', thicknessAssignment=FROM_SECTION
            )

        aim_region = self.aim_part3.sets['zc-c']
        self.aim_part3.SectionAssignment(region=aim_region, sectionName='gj-hnt', offset=0.0,
            offsetType=MIDDLE_SURFACE, offsetField='',
            thicknessAssignment=FROM_SECTION)

        aim_region = self.aim_part3.sets['zc-gang']
        self.aim_part3.SectionAssignment(region=aim_region, sectionName='gang', offset=0.0,
            offsetType=MIDDLE_SURFACE, offsetField='',
            thicknessAssignment=FROM_SECTION)
            
        aim_region = self.aim_part3.sets['diban']
        self.aim_part3.SectionAssignment(region=aim_region, sectionName='diban', offset=0.0,
            offsetType=MIDDLE_SURFACE, offsetField='',
            thicknessAssignment=FROM_SECTION)
        
        # 3.4 设置wall-zc的梁截面方向
        region=self.aim_part3.sets['zc-c']
        self.aim_part3.assignBeamSectionOrientation(\
            region=region, method=N1_COSINES, n1=(0.0, 0.0, -1.0)
            )
        region=self.aim_part3.sets['zc-gang']
        self.aim_part3.assignBeamSectionOrientation(\
            region=region, method=N1_COSINES, n1=(0.0, 0.0, -1.0)
            )

    def load_pressure_process(self):

        # 结构整体的重力场 || 用于地应力平衡
        self.aim_model.Gravity(\
            name='gravity', createStepName='geo', comp2=-9.8, distributionType=UNIFORM, field=''
            )

    def load_pressure_process_v2(self, zjnt_pressure=-2000000.0):

        # 1 结构整体的重力场 || 用于地应力平衡
        self.aim_model.Gravity(\
            name='gravity', createStepName='geo', comp2=-9.8, distributionType=UNIFORM, field=''
            )
        
        # 2 压强 * 2(两侧)
        region = self.aim_assembly.instances[\
            '{}-1'.format(self.part2_name)].surfaces['yaqiang1']

        self.aim_model.Pressure(name='Load-1', createStepName='zjnt', 
            region=region, distributionType=UNIFORM, field='', 
            magnitude=zjnt_pressure, amplitude=UNSET)

        region = self.aim_assembly.instances[\
            '{}-1'.format(self.part2_name)].surfaces['yaqiang2']

        self.aim_model.Pressure(name='Load-2', createStepName='zjnt', 
            region=region, distributionType=UNIFORM, field='', 
            magnitude=zjnt_pressure, amplitude=UNSET)

    def boundray_process(self):

        # 1 BC-3
        region = self.aim_assembly.instances['{}-1'.format(self.part3_name)].sets['zc-x']
        self.aim_model.DisplacementBC(name='BC-3',
            createStepName='Initial', region=region, u1=SET, u2=SET, ur3=UNSET,
            amplitude=UNSET, distributionType=UNIFORM, fieldName='',
            localCsys=None)

        # 2 BC-4
        region = self.aim_assembly.sets['Set-1']
        self.aim_model.PorePressureBC(name='BC-4',
            createStepName='Initial', region=region, distributionType=UNIFORM,
            fieldName='', magnitude=0.0)

        # 3 BC-X
        region = self.aim_assembly.instances['{}-1'.format(self.part2_name)].sets['X']
        self.aim_model.DisplacementBC(name='BC-X',
            createStepName='Initial', region=region, u1=SET, u2=UNSET, ur3=UNSET,
            amplitude=UNSET, distributionType=UNIFORM, fieldName='',
            localCsys=None)

        # 4 BC-Y
        region = self.aim_assembly.instances['{}-1'.format(self.part2_name)].sets['Y']
        self.aim_model.DisplacementBC(name='BC-Y',
            createStepName='Initial', region=region, u1=SET, u2=SET, ur3=UNSET,
            amplitude=UNSET, distributionType=UNIFORM, fieldName='',
            localCsys=None)

    def boundray_process_v2(self):

        # 1 BC-2
        region = self.aim_assembly.instances['{}-1'.format(self.part3_name)].sets['zc-x']
        self.aim_model.XsymmBC(name='BC-2', createStepName='Initial', region=region, 
            localCsys=None)

        # 2 BC-X
        region = self.aim_assembly.instances['{}-1'.format(self.part2_name)].sets['X']
        self.aim_model.DisplacementBC(name='BC-X',
            createStepName='Initial', region=region, u1=SET, u2=UNSET, ur3=UNSET,
            amplitude=UNSET, distributionType=UNIFORM, fieldName='',
            localCsys=None)

        # 3 BC-Y
        region = self.aim_assembly.instances['{}-1'.format(self.part2_name)].sets['Y']
        self.aim_model.DisplacementBC(name='BC-Y',
            createStepName='Initial', region=region, u1=SET, u2=SET, ur3=SET,
            amplitude=UNSET, distributionType=UNIFORM, fieldName='',
            localCsys=None)

    def predefine_field_process(self):

        # 1 Predefined Field-1
        region = self.aim_assembly.instances['{}-1'.format(self.part2_name)].sets['soil']
        self.aim_model.Field(name='Predefined Field-1',
            createStepName='Initial', region=region, distributionType=UNIFORM,
            crossSectionDistribution=CONSTANT_THROUGH_THICKNESS,
            fieldVariableNum=1, magnitudes=(1.0, ))

        # 2 Predefined Field-2
        region = self.aim_assembly.instances['{}-1'.format(self.part2_name)].sets['sjnt']
        self.aim_model.Field(name='Predefined Field-2',
            createStepName='Initial', region=region, distributionType=UNIFORM,
            crossSectionDistribution=CONSTANT_THROUGH_THICKNESS,
            fieldVariableNum=1, magnitudes=(1.0, ))

        self.aim_model.predefinedFields['Predefined Field-2'].setValuesInStep(
            stepName='add-zjnt', magnitudes=(2.0, ))

        # 3 Predefined Field-3
        region = self.aim_assembly.sets['Set-2']
        self.aim_model.VoidsRatio(name='Predefined Field-3',
            region=region, voidsRatio1=1.0, distributionType=UNIFORM,
            variation=CONSTANT_RATIO)

    def predefine_field_process_v2(self):

        # 1 Predefined Field-1
        region = self.aim_assembly.instances['{}-1'.format(self.part2_name)].sets['soil']
        self.aim_model.Field(name='Predefined Field-1',
            createStepName='Initial', region=region, distributionType=UNIFORM,
            crossSectionDistribution=CONSTANT_THROUGH_THICKNESS,
            fieldVariableNum=1, magnitudes=(1.0, ))

        # 2 Predefined Field-2
        region = self.aim_assembly.instances['{}-1'.format(self.part2_name)].sets['sjnt']
        self.aim_model.Field(name='Predefined Field-2',
            createStepName='Initial', region=region, distributionType=UNIFORM,
            crossSectionDistribution=CONSTANT_THROUGH_THICKNESS,
            fieldVariableNum=1, magnitudes=(1.0, ))

        self.aim_model.predefinedFields['Predefined Field-2'].setValuesInStep(
            stepName='zjnt', magnitudes=(2.0, ))

    def mesh_process(self):

        # 1 chenqi
        self.aim_part1.seedPart(\
            size=self.chenqi_mesh_size,
            deviationFactor=0.1, minSizeFactor=0.1
            )
        self.aim_part1.generateMesh()

        # 指派特殊网格属性self.aim_part1
        pickedRegions =tools_get_whole_region(self.aim_part1.faces)

        self.aim_part1.setMeshControls(\
            regions=pickedRegions, elemShape=QUAD, technique=STRUCTURED
            )

        elemType1 = mesh.ElemType(elemCode=CPE4P, elemLibrary=STANDARD)
        elemType2 = mesh.ElemType(elemCode=UNKNOWN_TRI, elemLibrary=STANDARD)

        self.aim_part1.setElementType(\
            regions=(pickedRegions,), elemTypes=(elemType1, elemType2)
            )

        self.aim_part1.generateMesh()

        # 2 soil
        self.aim_part2.seedPart(\
            size=self.soil_mesh_size,
            deviationFactor=0.1, minSizeFactor=0.1
            )

        # 指派特殊网格属性self.aim_part2
        aim_region = tools_get_whole_region(self.aim_part2.faces)
        self.aim_part2.setMeshControls(\
            regions=self.aim_region_soil, elemShape=QUAD, technique=STRUCTURED
            )

        # soil 整体
        elemType1 = mesh.ElemType(elemCode=CPE4P, elemLibrary=STANDARD)
        elemType2 = mesh.ElemType(elemCode=UNKNOWN_TRI, elemLibrary=STANDARD)

        self.aim_part2.setElementType(\
            regions=(self.aim_region_soil,), elemTypes=(elemType1, elemType2)
            )

        # soil chenqi sjnt
        elemType1 = mesh.ElemType(elemCode=CPE4, elemLibrary=STANDARD)
        elemType2 = mesh.ElemType(elemCode=CPE3, elemLibrary=STANDARD)

        self.aim_part2.setElementType(\
            regions=(self.aim_region_soil_cq,), elemTypes=(elemType1, elemType2)
            )

        self.aim_part2.setElementType(\
            regions=(self.aim_region_soil_sjnt,), elemTypes=(elemType1, elemType2)
            )

        self.aim_part2.generateMesh()

        # 3 wall-zc
        self.aim_part3.seedPart(\
            size=self.wall_zc_mesh_size,
            deviationFactor=0.1, minSizeFactor=0.1
            )

        # 指派特殊网格属性
        elemType1 = mesh.ElemType(elemCode=CPE4, elemLibrary=STANDARD,
            secondOrderAccuracy=OFF, hourglassControl=DEFAULT,
            distortionControl=DEFAULT)
        elemType2 = mesh.ElemType(elemCode=CPE3, elemLibrary=STANDARD)

        pickedRegions =(tools_get_whole_region(self.aim_part3.faces), )

        self.aim_part3.setElementType(\
            regions=pickedRegions, elemTypes=(elemType1, elemType2)
            )

        self.aim_part3.generateMesh()

    def mesh_process_v2(self):

        # 1 soil ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.aim_part2.seedPart(\
            size=self.soil_mesh_size,
            deviationFactor=0.1, minSizeFactor=0.1
            )

        # 指派特殊网格属性self.aim_part2
        aim_region = tools_get_whole_region(self.aim_part2.faces)
        self.aim_part2.setMeshControls(\
            regions=self.aim_region_soil, elemShape=QUAD, technique=STRUCTURED
            )

        # soil 整体
        elemType1 = mesh.ElemType(elemCode=CPE4, elemLibrary=STANDARD)
        elemType2 = mesh.ElemType(elemCode=CPE3, elemLibrary=STANDARD)

        self.aim_part2.setElementType(\
            regions=(self.aim_region_soil,), elemTypes=(elemType1, elemType2)
            )

        # soil chenqi sjnt
        elemType1 = mesh.ElemType(elemCode=CPE4, elemLibrary=STANDARD)
        elemType2 = mesh.ElemType(elemCode=CPE3, elemLibrary=STANDARD)

        self.aim_part2.setElementType(\
            regions=(self.aim_region_soil_cq,), elemTypes=(elemType1, elemType2)
            )

        self.aim_part2.setElementType(\
            regions=(self.aim_region_soil_sjnt,), elemTypes=(elemType1, elemType2)
            )

        self.aim_part2.generateMesh()

        # 2 wall-zc ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.aim_part3.seedPart(\
            size=self.wall_zc_mesh_size,
            deviationFactor=0.1, minSizeFactor=0.1
            )

        # 指派特殊网格属性
        elemType1 = mesh.ElemType(elemCode=CPE4, elemLibrary=STANDARD,
            secondOrderAccuracy=OFF, hourglassControl=DEFAULT,
            distortionControl=DEFAULT)
        elemType2 = mesh.ElemType(elemCode=CPE3, elemLibrary=STANDARD)

        pickedRegions =(tools_get_whole_region(self.aim_part3.faces), )

        self.aim_part3.setElementType(\
            regions=pickedRegions, elemTypes=(elemType1, elemType2)
            )

        self.aim_part3.generateMesh()
        
        # 3 chenqi ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.aim_part1.seedPart(\
            size=self.soil_mesh_size,
            deviationFactor=0.1, minSizeFactor=0.1
            )

        # 指派特殊网格属性self.aim_part1
        aim_region = tools_get_whole_region(self.aim_part1.faces)
        self.aim_part1.setMeshControls(\
            regions=self.aim_region_chenqi, elemShape=QUAD, technique=STRUCTURED
            )

        # 指派网格类型
        elemType1 = mesh.ElemType(elemCode=CPE4, elemLibrary=STANDARD)
        elemType2 = mesh.ElemType(elemCode=CPE3, elemLibrary=STANDARD)

        self.aim_part1.setElementType(\
            regions=(self.aim_region_chenqi,), elemTypes=(elemType1, elemType2)
            )

        self.aim_part1.generateMesh()

    def create_inp(self):

        self.aim_assembly.regenerate()
        mdb.Job(name=self.model_name, model=self.model_name, description='',
            type=ANALYSIS, atTime=None, waitMinutes=0, waitHours=0, queue=None,
            memory=90, memoryUnits=PERCENTAGE, getMemoryFromAnalysis=True,
            explicitPrecision=SINGLE, nodalOutputPrecision=SINGLE, echoPrint=OFF,
            modelPrint=OFF, contactPrint=OFF, historyPrint=OFF, userSubroutine='',
            scratch='', resultsFormat=ODB, numCpus=1, numGPUs=0)
        mdb.jobs[self.model_name].writeInput(consistencyChecking=OFF)
        # del mdb.models[self.model_name]


def mdb_process_api(test_name, F_Ht=37.2, F_Lwt_ratio=1.0, F_We=30.0, F_He_ratio=1.0, F_Dt=6.2, F_Lct=3.0, F_Dcap=0.5, \
    F_Tw=0.8, F_tlining=0.5, F_Lc=8.0, \
    soil_fai=10.0, soil_c=50000.0, soil_E=30000000.0, soil_density=1800.0, soil_xmu=0.49, \
    mesh_size=0.5, zjnt_pressure=-180000.0, \
    step_zjnt_maxNumInc=1000, step_zjnt_minInc=1e-5):

    MP = mdbProcess(\
        mn=test_name
        )

    # <用户自定义参数> 可变参数
    Ht = F_Ht  # 隧道顶部深度
    He = F_He_ratio*Ht  # 开挖深度 0.5/1/2Ht (**开挖深度一定要足够大)
    Dt = F_Dt  # 隧道外径(固定值)
    Lct = F_Lct  # 注浆囊体右侧离隧道左侧距离(固定值)
    Dcap = F_Dcap  # 胶囊宽度
    Lc = F_Lc  # 胶囊高度
    F_B = F_We  # 开挖半宽
    Tw = F_Tw  # 挡土墙宽度
    t_lining = F_tlining  # 衬砌厚度
    Lwt = F_Lwt_ratio*He  # 挡土墙右侧与隧道轴线距离 0.5/1.0He (lwt0.5不行)
    dtq_ratio_para = 2.0  # 挡土墙高度是开挖深度的2倍

    # ----------------------------------------------------------
    """
    外框架尺寸处理
    再设置一个系数，系数越大模型越大，用户可改
    """
    len_para = 1.5  # 长度方向系数
    wid_para = 2  # 宽度方向系数

    part_len = 0.0
    part_wid = 0.0

    # 1模型长度
    part_len = (F_B+Tw+Lwt+Dt*0.5)*len_para

    # 2模型宽度 || 202509版本 || 模型宽度满足挡土墙深度或隧道底部深度的1.3倍
    # 挡土墙深度
    dtq_sd = He*dtq_ratio_para
    # 隧道底部
    sd_sd = Ht+Dt
    # 模型宽度
    # || 如果挡土墙更深
    if dtq_sd > sd_sd:
        part_wid = dtq_sd*1.1
    # || 如果隧道更深
    else:
        part_wid = sd_sd*2.0
    
    # 3 [补充逻辑] || 20250930版本 || 模型长度和宽度均至少4He
    four_he = 4.0*He
    if part_len <= four_he:
        part_len = four_he
    if part_wid <= four_he:
        part_wid = four_he

    # 4 [补充逻辑] || 20251029版本 || 底层土参数控制
    # 当上层土弹模＜10 MPa，底层土的弹模为上层土的10倍
    if soil_E < 10000000.0:
        soil_2_E = soil_E * 10.0
    # 否则固定50 MPa
    else:
        soil_2_E = 50000000.0
    
    # ----------------------------------------------------------
    """
    外框架尺寸处理2 || 20250903
    长度和宽度的比例不能超过2，否则短边取长边的0.5倍
    """
    if part_len>part_wid:
        if part_len/part_wid>2.0:
            part_wid = part_len*0.5

    if part_wid>part_len:
        if part_wid/part_len>2.0:
            part_len = part_wid*0.5

    # API || 整体结构参数
    MP.set_whole_structure(\
        part_len=part_len, \
        part_wid=part_wid
        )

    # API || 隧道参数
    MP.set_suidao_para(\
        Dt=Dt, \
        Ht=Ht, \
        tlining=t_lining
        )
    # API || 胶囊参数
    MP.set_jiaonang_para(\
        Lct=3.0, \
        Dc=Dcap, \
        Lc=Lc
        )
    # API || 挡土墙参数
    MP.set_dangtu_para(\
        Tw=Tw, \
        Lwt=Lwt, \
        dtrt=dtq_ratio_para
        )
    # API || 开挖参数
    MP.set_kaiwa_para(\
        He=He, \
        F_B=F_B
        )
    
    # 网格尺寸控制
    MP.chenqi_mesh_size = mesh_size
    MP.aim_region_soil_cq = mesh_size
    MP.aim_region_soil_sjnt = mesh_size

    MP.get_abaqus_object()
    # modeling
    MP.part1_chenqi()
    MP.part3_wall_zc()  # 逻辑调整，先生成wall-zc部件，因为部分数据soil要用
    MP.part2_soil()  # ** soil拆分逻辑在内部判定

    # set and surface
    MP.part1_set()
    MP.part1_surface()
    MP.part2_set()
    MP.part2_surface_v2()
    MP.part3_set_v2()
    MP.part3_surface_v2()

    # material and section
    MP.material_and_section_process_v2(\
        soil_E=soil_E,
        soil_fai=soil_fai,
        soil_c=soil_c,
        soil_density=soil_density,
        soil_xmu=soil_xmu,
        soil_2_E=soil_2_E
        )

    # root assembly ||
    MP.assembly_process_v1()

    # mesh process
    MP.mesh_process_v2()

    # mesh node set || 历程输出监测区在此设置
    MP.mesh_node_set()

    # step process
    MP.step_process_v2(step_zjnt_maxNumInc, step_zjnt_minInc)

    # interaction process
    MP.interaction_process_v2()

    # load process
    MP.load_pressure_process_v2(zjnt_pressure=zjnt_pressure)
    MP.boundray_process_v2()
    MP.predefine_field_process_v2()

    # create inp
    MP.create_inp()


if __name__=="__main__":

    print("\nProgram start!")

    # MDB模块业务
    mdb_process_api(\
        test_name="TEST_DEBUG",
        F_Ht=12.4,
        F_Lwt_ratio=1.0,
        F_We=15.0,
        F_He_ratio=1.0,
        F_Dt=6.2,
        F_Lct=3.0,
        F_Dcap=0.5,
        soil_fai=20.0,
        soil_c=10000.0,
        soil_E=2000000.0,
        soil_density=1800.0,
        soil_xmu=0.49,
        mesh_size=0.5,
        zjnt_pressure=-2000000.0,
        step_zjnt_maxNumInc=1000, 
        step_zjnt_minInc=1e-5
        )

    print("\nProgram end!")
