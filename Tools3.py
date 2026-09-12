#- * -coding: UTF-8- * -
# chenhongcheng3097@163.com
# 2025-7-22 v1  XY238
# 2025-8-28 v2  XY238  || 用户不得自行添加历程输出
# 2025-9-12 v3  XY238  增加zjnt面积计算
# 2025-10-23 v3  XY238

from abaqus import *
from abaqusConstants import *
from odbAccess import *
from textRepr import *
import xyPlot
import csv
import os
import time
import displayGroupOdbToolset as dgo


def get_odb_name_list():

    odb_name_list = []
    for ite in os.listdir(os.getcwd()):
        if ite.endswith(".odb"):
            odb_name_list.append(ite[:-4])

    return odb_name_list


class odbProcess:
    """
    __version__1 20250901
    """
    def __init__(self):

        # user define para
        self.odb_name = None
        self.instance_name = "SOIL-1"
        self.instance_name2 = "WALL-ZC-1"
        self.instance_name3 = "CHENQI-1"

        # abaqus object
        self.__aim_odb = None
        self.__aim_assembly = None
        self.__aim_instance = None
        self.__aim_instance2 = None
        self.__aim_instance3 = None
        self.__aim_step = None
        self.__aim_region = None

        # process data
        self.step_name_list = []
        self.__hist_region_name_list = []

        # zjnt 场输出变量
        self.__zjnt_ele_set_name = "SJNT"
        self.__zjnt_node_set_name = "SJNT"
        self.__zjnt_ele_set_object = None  # zjnt的单元集实例化对象
        self.__zjnt_node_set_object = None  # zjnt的节点集实例化对象
        self.__zjnt_ele_id_list = None  # zjnt的单元label列表
        self.__zjnt_ele_connect_list = None  # zjnt的单元相邻节点列表 [[], [], [], ...]
        self.__zjnt_node_id_list = None  # zjnt的节点label列表
        self.__zjnt_node_loc_list = None  # zjnt的节点变形前坐标列表 [[], [], [], ...]

    def __get_aim_odb(self):

        # abaqus api || odb & assembly & instance & step
        # open odb
        session.mdbData.summary()

        # 异常处理
        status_check = True
        index_num = 0
        while status_check:
            index_num += 1
            try:
                o1 = session.openOdb(name="{}.odb".format(self.odb_name))
                status_check = False
            except:
                print("odb open fail, wait 5s")
                time.sleep(5)

            if index_num>=5:
                print("\nOdb open num over5 {}".format(self.odb_name))
                return False

        # get Viewport
        try:
            session.viewports['Viewport: 1'].setValues(displayedObject=o1)
        except:
            print("\nOdb open error {}".format(self.odb_name))
            return False
        session.linkedViewportCommands.setValues(_highlightLinkedViewports=False)
        odbName=session.viewports[session.currentViewportName].odbDisplay.name

        # get odb object
        self.__aim_odb = session.odbs["{}.odb".format(self.odb_name)]
        self.__aim_assembly = self.__aim_odb.rootAssembly
        self.__aim_instance = self.__aim_assembly.instances[self.instance_name]
        self.__aim_instance2 = self.__aim_assembly.instances[self.instance_name2]
        self.__aim_instance3 = self.__aim_assembly.instances[self.instance_name3]

        return True

    def odb_close(self):

        self.__aim_odb.close()

    def get_abaqus_object(self):
        """
        get odb & step object
        """
        odb_status = self.__get_aim_odb()
        if not odb_status:
            return False
        else:
            return True

    def __get_history_region_name_list(self):

        print("\nProcess on get hist region, pls wait")

        self.step_name_list = self.__aim_odb.steps.keys()
        self.__hist_region_name_list = self.__aim_odb.steps[\
            self.step_name_list[0]].historyRegions.keys()

        print("\nGet hist region number --> {}"
            .format(len(self.__hist_region_name_list)))

    def __get_history_value(self, step_name, var_name):

        # print(self.aim_region.historyOutputs.keys())
        try:
            aim_data = self.__aim_region.historyOutputs[var_name].data

            time_list = [float(ite[0]) for ite in aim_data]
            value_list = [float(ite[1]) for ite in aim_data]

            return time_list, value_list
        except:
            print("{A}_{B}, {C} is not exist, pass"\
                    .format(A=self.odb_name, B=step_name, C=var_name))
            return [], []

    def __csv_out(self, csv_name, title_list, time_list, value_list):
        """
        :param csv_name: str
        :param title_list: [str, str, str, ...]
        :param time_list: [float, float, float, ....]
        :param value_list: [[], [], [], ...]
        """

        with open("OutPutData_{A}_{B}.csv".format(A=self.odb_name, B=csv_name), "wb") as writeFile:

            f_writer = csv.writer(writeFile)

            # for titles
            f_writer.writerow(title_list)
            # for value
            for i in range(len(value_list[0])):

                row_data = [time_list[i]]
                for j in range(len(value_list)):
                    row_data.append(value_list[j][i])

                f_writer.writerow(row_data)

    def __csv_out_row(self, csv_name, row_list):

        with open("OutPutData_{A}_{B}.csv".format(A=self.odb_name, B=csv_name), "wb") as writeFile:

            f_writer = csv.writer(writeFile)

            # for value
            for ite in row_list:
                f_writer.writerow(ite)

    def __csv_out_catogray_v1(self, csv_name, title_list, time_list, value_list):
        """
        20250921 csv分类别存储
        v1::密集监测网格按照单元输出
        :param csv_name: str
        :param title_list: [str, str, str, ...]
        :param time_list: [float, float, float, ....]
        :param value_list: [[], [], [], ...]
        """

        # 分类预设
        startwiths_list = ["ZJNT_HIST", "TUNNEL", "WALL_Y", "GS_X", "EB_X", "MJ-SD", "MJ-DB"]

        # 对于每一个分类，分别执行输出流程
        for startwith_ite in startwiths_list:

            with open("OutPutData_{A}_{B}_{C}.csv".format(A=self.odb_name, B=csv_name, C=startwith_ite), "wb") as writeFile:

                f_writer = csv.writer(writeFile)

                # 1 获取目标数据表头及表头对应数据表编号
                index_list = []
                f_title_list = ["time"]
                for i in range(len(title_list)):
                    if startwith_ite in title_list[i]:
                        index_list.append(i-1)  # 减一的原因是，需要扣除标题行的部分
                        f_title_list.append(title_list[i])

                # 2 获取目标value_list
                f_value_list = []
                for index_num in index_list:
                    f_value_list.append(value_list[index_num])

                # dBUG 单元历程输出，四边形网格，包含四个角点，求平均值
                ff_title_list, ff_value_list = self.__tools_duplicated_check(f_title_list, f_value_list)

                # for titles
                f_writer.writerow(ff_title_list)
                # for value
                for i in range(len(ff_value_list[0])):

                    row_data = [time_list[i]]
                    for j in range(len(ff_value_list)):
                        row_data.append(ff_value_list[j][i])

                    f_writer.writerow(row_data)

    def __csv_out_catogray_v2(self, csv_name, title_list, time_list, value_list):
        """
        20250921 csv分类别存储
        :param csv_name: str
        :param title_list: [str, str, str, ...]
        :param time_list: [float, float, float, ....]
        :param value_list: [[], [], [], ...]
        """

        # 分类预设
        startwiths_list = ["ZJNT_HIST", "TUNNEL", "WALL_Y", "GS_X", "EB_X", "MJ-SD", "MJ-DB"]

        # 对于每一个分类，分别执行输出流程
        final_u1 = None
        for startwith_ite in startwiths_list:

            with open("OutPutData_{A}_{B}_{C}.csv".format(A=self.odb_name, B=csv_name, C=startwith_ite), "wb") as writeFile:

                f_writer = csv.writer(writeFile)

                # 1 获取目标数据表头及表头对应数据表编号
                index_list = []
                mo_index = None
                f_title_list = ["time"]
                for i in range(len(title_list)):
                    if startwith_ite in title_list[i]:
                        index_list.append(i)
                        f_title_list.append(title_list[i])

                    # monitor
                    if "TUNNEL_7_LEFT_U1" in title_list[i]:
                        mo_index = i

                # 2 for titles
                f_writer.writerow(f_title_list)

                # 3 for value
                for i in range(len(value_list)):

                    row_data = [time_list[i]]

                    # for each index
                    for index_num in index_list:
                        row_data.append(value_list[i][index_num])

                    f_writer.writerow(row_data)

                    # monitor
                    if mo_index is not None:
                        if i == len(value_list)-1:
                            final_u1 = value_list[i][mo_index]

        return final_u1

    @ staticmethod
    def __tools_duplicated_check(tile_list, value_list):
        """
        :param tile_list: 表头列表，第一列多一个time
        :param value_list: [[]. []. []. ...]
        """

        def find_duplicated_index(origin_list):

            index_dict = {}
            for index, element in enumerate(origin_list):

                if element in index_dict:
                    index_dict[element].append(index)
                else:
                    index_dict[element]=[index]

            return index_dict

        def get_avg_col(duplicat_list):
            """
            正常情况下，abq同一单元相邻节点的数据长度本身就是一致的，所以不做异常处理
            """
            new_list = []
            for i in range(len(duplicat_list[0])):

                row_list = []
                for j in range(len(duplicat_list)):
                    row_list.append(duplicat_list[j][i])

                new_list.append(sum(row_list)/len(row_list))

            return new_list

        # 1 首先判断是否有重复
        title_set = set(tile_list[1:])
        if len(title_set)==len(value_list):
            return tile_list, value_list

        # 2 如果存在重复项，则对重复项求平均值，对应单元数
        # 获取原列表中唯一元素及重复索引的位置
        index_dict = find_duplicated_index(tile_list[1:])

        # 3 新title_list
        new_title_list = index_dict.keys()
        new_title_list.sort()
        # print(new_title_list)
        f__new_title_list = [tile_list[0]]
        f__new_title_list.extend(new_title_list)

        # 4 新value_list
        f_new_value_list = []
        for title_key in new_title_list:
            index_list = index_dict[title_key]

            duplicat_list = []  # [[], [], [], ...]
            # 获取对应的重复列，组装二维列表
            for col_index in index_list:
                duplicat_list.append(value_list[col_index])

            # 生成平均值列
            f_new_value_list.append(get_avg_col(duplicat_list))

        return f__new_title_list, f_new_value_list

    def __tools1_by_hist_data(self, region_name, region_description, mo_data_list):

        region_time = []
        u1_region_value = []
        u2_region_value = []
        # for each step
        for j in range(len(self.step_name_list)):
            step_name = self.step_name_list[j]
            self.__aim_step = self.__aim_odb.steps[step_name]

            # 1 update aim region
            try:
                self.__aim_region = self.__aim_step.historyRegions[\
                    region_name]
            except:
                print("{A}_{B}, {C} is not exist, pass"\
                    .format(A=self.odb_name, B=step_name, C=region_name))
                continue

            # 2 get region value || U
            u1_time_list, u1_aim_data = self.__get_history_value(step_name, "U1")
            u2_time_list, u2_aim_data = self.__get_history_value(step_name, "U2")
            region_time.extend(u1_time_list)
            u1_region_value.extend(u1_aim_data)
            u2_region_value.extend(u2_aim_data)

        if "TUNNEL_7_LEFT" in region_description:
            mo_data_list = u1_aim_data

        return mo_data_list, region_time, u1_region_value, u2_region_value

    def __tools_set_display_frame(self):

        session.odbData['{}.odb'.format(self.odb_name)].setValues(\
            activeFrames=((self.step_name, ('0:-1', )), )
            )

    def __component_data(self, var_name, ins_name, node_describ):

        node_set_name = "{A}.{B}".format(A=ins_name, B=node_describ)

        xyList = xyPlot.xyDataListFromField(odb=self.__aim_odb, outputPosition=NODAL, variable=((
            'U', NODAL, ((COMPONENT, var_name), )), ), nodeSets=(
            node_set_name.replace(" ", ""), ))

        print("\nGet {}".format(var_name))
        return xyList

    @ staticmethod
    def trash():
        # trash
        total_num = len(session.xyDataObjects.keys())
        for ite in session.xyDataObjects.keys():
            del session.xyDataObjects[ite]
            print("\nClear {} success".format(ite))

    def __get_field_data(self, node_list, node_describ_list):

        def data_frame(origin_data):

            time_data = [float(ite[0]) for ite in origin_data]
            aim_data = [float(ite[1]) for ite in origin_data]

            return time_data, aim_data

        title_list = []
        time_list = []
        value_list = []  # [[], []]

        # for each node label
        for j in range(len(node_list)):

            node_label = node_list[j]
            node_describ = node_describ_list[j]
            print("\nProcess on {}".format(node_describ))

            title_list.append("{A}-{B}"\
                .format(A=node_describ, B="U1"))

            title_list.append("{A}-{B}"\
                .format(A=node_describ, B="U2"))

            # set frames
            # self.__tools_set_display_frame()

            # get time and values
            # 20250920 dBUG，有两个装配体，自动适配
            try:
                U1_xyList = self.__component_data("U1", self.instance_name, node_describ)
                time_data, U1_aim_data = data_frame(U1_xyList[0])

                U2_xyList = self.__component_data("U2", self.instance_name, node_describ)
                time_data, U2_aim_data = data_frame(U2_xyList[0])
            except:
                U1_xyList = self.__component_data("U1", self.instance_name2, node_describ)
                time_data, U1_aim_data = data_frame(U1_xyList[0])

                U2_xyList = self.__component_data("U2", self.instance_name2, node_describ)
                time_data, U2_aim_data = data_frame(U2_xyList[0])

            # update data frame
            time_list = time_data
            value_list.append(U1_aim_data)
            value_list.append(U2_aim_data)
            if "TUNNEL_7_LEFT" in node_describ:
                mo_data_list = U1_aim_data

        self.trash()
        return title_list, time_list, value_list, mo_data_list

    def __get_field_zjnt_loc(self, aim_frame):
        """
        用户业务：基于坐标，获取zjnt当前帧实时坐标 || with node subset, for fast speed!
        """
        # get aim field
        aim_filed_U = aim_frame.fieldOutputs["U"]

        # get subset
        aim_data_U = aim_filed_U.getSubset(\
            region=self.__zjnt_node_set_object
            ).values

        # <data>
        node_id_list = []
        node_U1_list = []
        node_U2_list = []

        # for each node
        for ite in aim_data_U:
            node_id_list.append(int(ite.nodeLabel))
            node_U1_list.append(float(ite.data[0]))
            node_U2_list.append(float(ite.data[1]))

        # <data>
        node_new_loc_list = []
        area_list = []

        # calculate node x/y
        for k in range(len(self.__zjnt_node_id_list)):

            aim_node_id = self.__zjnt_node_id_list[k]
            origin_node_x = self.__zjnt_node_loc_list[k][0]
            origin_node_y = self.__zjnt_node_loc_list[k][1]

            index_num = node_id_list.index(aim_node_id)
            disp_x = node_U1_list[index_num]
            disp_y = node_U2_list[index_num]

            now_node_x = origin_node_x+disp_x
            now_node_y = origin_node_y+disp_y

            node_new_loc_list.append([now_node_x, now_node_y])

        # calculate ele area
        for k in range(len(self.__zjnt_ele_id_list)):

            # <data>
            ele_connect_node_loc_list = []

            # connect node id
            connet_node_id_list = self.__zjnt_ele_connect_list[k]

            # for each node
            for connect_node_id in connet_node_id_list:
                index_num = node_id_list.index(connect_node_id)
                new_node_loc = node_new_loc_list[index_num]
                ele_connect_node_loc_list.append(new_node_loc)

            # calculate area || triangle
            x1 = ele_connect_node_loc_list[0][0]
            y1 = ele_connect_node_loc_list[0][1]

            x2 = ele_connect_node_loc_list[1][0]
            y2 = ele_connect_node_loc_list[1][1]

            x3 = ele_connect_node_loc_list[2][0]
            y3 = ele_connect_node_loc_list[2][1]

            x4 = ele_connect_node_loc_list[3][0]
            y4 = ele_connect_node_loc_list[3][1]

            ele_area = 0.5*abs((x1*y2 + x2*y3 + x3*y4 + x4*y1) - \
                (y1*x2 + y2*x3 + y3*x4 + y4*x1))

            area_list.append(ele_area)

        # get zjnt total area
        total_area = sum(area_list)

        return total_area

    def __get_field_value_for_single_frame(self, aim_frame, node_set_object, aim_data_name):
        
        # get aim field
        aim_filed = aim_frame.fieldOutputs[aim_data_name]

        # get subset
        aim_data = aim_filed.getSubset(\
            region=node_set_object
            ).values
        
        # 对于U1
        value1 = float(aim_data[0].data[0])
        # 对于U2
        value2 = float(aim_data[0].data[1])

        return value1, value2

    def __field_data_for_single_step(self, step_name):

        # get aim step
        aim_step = self.__aim_odb.steps[step_name]

        # get frame num
        aim_frames = aim_step.frames
        frame_nums = len(aim_frames)

        # <single frame data>
        step_time_list = []
        area_data_list = []

        # for each frame
        for i in range(frame_nums):

            print("\nProcess on step {A} || {B}/{C}"\
                .format(A=step_name, B=i+1, C=frame_nums))

            # 1 single frame object
            aim_frame = aim_frames[i]

            # 2 get step time
            frame_description = aim_frame.description
            frame_index = frame_description.index("Step Time =")
            step_time = float(frame_description[frame_index+11:])
            step_time_list.append(step_time)

            # 3 用户场输出需求1：zjnt面积计算
            total_area = self.__get_field_zjnt_loc(aim_frame)
            area_data_list.append(total_area)

        return step_time_list, area_data_list

    @ staticmethod
    def __tools_get_ele_info(ele_object):

        ele_id_list = []
        ele_connect_list = []
        for ite in ele_object:
            ele_id_list.append(int(ite.label))
            ele_connect_list.append(list(ite.connectivity))
        return ele_id_list, ele_connect_list

    @ staticmethod
    def __tools_get_node_info(node_object):

        node_id_list = []
        node_loc_list = []
        for ite in node_object:
            node_id_list.append(int(ite.label))
            node_loc_list.append(list(ite.coordinates))
        return node_id_list, node_loc_list

    def zjnt_ele_node_info(self):

        # get set object
        self.__zjnt_ele_set_object = self.__aim_instance.elementSets[\
            self.__zjnt_ele_set_name]
        self.__zjnt_node_set_object = self.__aim_instance.nodeSets[\
            self.__zjnt_node_set_name]

        # get ele info
        self.__zjnt_ele_id_list, self.__zjnt_ele_connect_list = self.__tools_get_ele_info(\
            self.__zjnt_ele_set_object.elements)

        # get node info
        self.__zjnt_node_id_list, self.__zjnt_node_loc_list = self.__tools_get_node_info(\
            self.__zjnt_node_set_object.nodes)

    def user_define_hist_process(self):

        self.__get_history_region_name_list()

        # for each region
        region_description_list = []
        time_list = []
        value_list = []
        mo_data_list = []
        total_var_name_list = []
        for i in range(len(self.__hist_region_name_list)):
            if i % 100==0:
                print("\nProcess on {A}/{B}"\
                    .format(A=i, B=len(self.__hist_region_name_list)))

            region_name = self.__hist_region_name_list[i]
            if region_name == "Assembly ASSEMBLY":
                continue

            # get_region_description
            region_description = self.__aim_odb.steps[\
                self.step_name_list[0]].historyRegions[\
                region_name].description
            region_description_list.append(\
                region_description[region_description.index("region")+6:])

            region_time = []
            # 先读取该region的全部var
            self.__aim_region = self.__aim_odb.steps[self.step_name_list[0]].historyRegions[\
                        region_name]
            var_name_list = self.__aim_region.historyOutputs.keys()
            region_value = {}
            for var_name in var_name_list:
                region_value[var_name] = []

            u1_region_value = []
            u2_region_value = []
            # for each step
            for j in range(len(self.step_name_list)):
                step_name = self.step_name_list[j]
                self.__aim_step = self.__aim_odb.steps[step_name]

                # 1 update aim region
                try:
                    self.__aim_region = self.__aim_step.historyRegions[\
                        region_name]
                except:
                    print("{A}_{B}, {C} is not exist, pass"\
                        .format(A=self.odb_name, B=step_name, C=region_name))
                    continue

                # 2 get region value || 有什么就抓什么
                for var_name in var_name_list:
                    time_list, aim_data = self.__get_history_value(step_name, var_name)
                    region_value[var_name].extend(aim_data)
                region_time.extend(time_list)

            if "TUNNEL_7_LEFT" in region_description:
                mo_data_list = region_value["U1"]  # 请检查1、是否输出U1；2、TUNNEL_7_LEFT名称是否正确，是否区分大小写

            for var_name in var_name_list:
                value_list.append(region_value[var_name])

            total_var_name_list.append(var_name_list)

        time_list = region_time
        title_list = ["time"]

        for j in range(len(region_description_list)):
            for var_name in total_var_name_list[j]:
                title_list.extend(["{A}_{B}"\
                    .format(A=region_description_list[j], B=var_name)])

        # csv output for a single region
        self.__csv_out_catogray_v1(csv_name="histData",
            title_list=title_list, time_list=time_list, value_list=value_list)

        if len(mo_data_list) != 0:
            final_u1 = mo_data_list[-1]
            final_time = time_list[-1]
        else:
            final_u1 = None
            final_time = None

        return final_u1, final_time

    def user_define_hist_process_by_session(self):
        """
        自动索引并输出全部region的历程输出
        """
        self.__get_history_region_name_list()

        # for each region
        region_description_list = []
        region_label_list = []
        mo_data_list = []
        title_list = ["time"]
        for i in range(len(self.__hist_region_name_list)):
            region_name = self.__hist_region_name_list[i]
            if region_name == "Assembly ASSEMBLY":
                continue

            # get_region_description and node num
            region_description = self.__aim_odb.steps[\
                self.step_name_list[0]].historyRegions[\
                region_name].description

            region_description_list.append(\
                region_description[region_description.index("region")+6:])

            region_label_list.append(region_description[\
                region_description.index("node")+4: region_description.index("region")
                ])

        # hist data by session
        t_list, time_list, value_list, mo_data_list = self.__get_field_data(\
            region_label_list, region_description_list)

        title_list.extend(t_list)

        # csv output for a single region
        self.__csv_out(csv_name="histData",
            title_list=title_list, time_list=time_list, value_list=value_list)

        if len(mo_data_list) != 0:
            final_u1 = mo_data_list[-1]
            final_time = time_list[-1]
        else:
            final_u1 = None
            final_time = None

        return final_u1, final_time

    def user_define_field_process(self):
        """
        全部基于fieldoutput完成
        """
        # <total data>
        step_time_list = []
        area_data_list = []

        # 1 get step name list
        step_name_list = self.__aim_odb.steps.keys()

        # 2 for each step
        for step_name in step_name_list:
            step_t_list, area_d_list = self.__field_data_for_single_step(step_name)
            step_time_list.extend(step_t_list)
            area_data_list.extend(area_d_list)

        # 3 out csv
        title_list = ["time", "zjnt_total_area"]
        self.__csv_out(csv_name="zjnt_area",
            title_list=title_list, time_list=step_time_list, value_list=[area_data_list])

    def user_define_field_process_for_monitor(self):
        """
        用户监测点输出，改fieldoutput版本来执行 <补丁>
        ::补丁形式，独立业务功能(按照用户要求改动)
        """
        def check_single_node_object(aim_objects):
            """
            return key_list
            """
            key_list = []
            object_list = []
            total_key_list = aim_objects.keys()
            for f_key in total_key_list:
                if len(aim_objects[f_key].nodes) != 1:
                    continue
                key_list.append(f_key)
                object_list.append(aim_objects[f_key])
            return key_list, object_list

        # <aim_value_type>
        aim_data_name_list = ["U"]
        aim_var_name_list = ["U1", "U2"]  # 手动核对名称及顺序，不能错

        # <data>
        mo_data_list = []
        title_list = []
        node_set_object_list = []  # 不带后缀，用于索引
        f_title_list = []  # 包含data名后缀，用于输出
        time_list = []
        value_list = []  # [[frame1], [frame2], [frame3], ...]  # 对应的就是row_data

        # 1 对于可能涉及的节点集 (通过对象是否唯一判断)
        # 1.1 intance1-soil
        node_set_object_1 = self.__aim_instance.nodeSets
        set_name_list, set_object_list = check_single_node_object(node_set_object_1)
        title_list.extend(set_name_list)
        node_set_object_list.extend(set_object_list)

        # 1.2 instance2-wall-zc
        node_set_object_2 = self.__aim_instance2.nodeSets
        set_name_list, set_object_list = check_single_node_object(node_set_object_2)
        title_list.extend(set_name_list)
        node_set_object_list.extend(set_object_list)

        # 1.3 instance3_chenqi
        node_set_object_3 = self.__aim_instance3.nodeSets
        set_name_list, set_object_list = check_single_node_object(node_set_object_3)
        title_list.extend(set_name_list)
        node_set_object_list.extend(set_object_list)

        # 2 update f title list
        for set_name in title_list:
            for aim_var_name in aim_var_name_list:
                f_title_list.append("{A}_{B}".format(A=set_name, B=aim_var_name))

        # 3 for each step
        step_name_list = self.__aim_odb.steps.keys()
        for step_name in step_name_list:

            # get aim frame and frame info
            aim_frames = self.__aim_odb.steps[step_name].frames
            frame_nums = len(aim_frames)

            # for each frame
            for i in range(frame_nums):
                print("\nProcess on step {A} || {B}/{C}"\
                    .format(A=step_name, B=i+1, C=frame_nums))

                # frame info
                aim_frame = aim_frames[i]
                frame_description = aim_frame.description
                frame_index = frame_description.index("Step Time =")
                time_list.append(float(frame_description[frame_index+11:]))

                # <data>
                value_row_data = []

                # for each key retun value || 顺序必须和2一致
                for node_set_object in node_set_object_list:
                    for aim_data_name in aim_data_name_list:

                        # get single frame data
                        value1, value2 = self.__get_field_value_for_single_frame(\
                            aim_frame, node_set_object, aim_data_name)
                        value_row_data.append(value1)
                        value_row_data.append(value2)
                
                value_list.append(value_row_data)
        
        # 4 写入csv表格
        final_u1 = self.__csv_out_catogray_v2(csv_name="histData",
            title_list=f_title_list, time_list=time_list, value_list=value_list)

        return final_u1, time_list[-1]

    def user_define_coord_process_v1(self):
        """
        v1::密集监测网格按照单元集输出
        基于历程输出集合，输出对应的坐标，并生成单独的csv文件，供用户读取、索引
        ::[统一格式]集合为单个节点或单个单元即为全部数据对象
        """
        def get_all_nodes_info(aim_instance):
            
            id_list = []
            coord_list = []
            aim_nodes = aim_instance.nodes
            for ite in aim_nodes:
                id_list.append(int(ite.label))
                coord_list.append(ite.coordinates)
            return id_list, coord_list

        def check_single_node_object(aim_objects):
            """
            return key_list
            """
            key_list = []
            total_key_list = aim_objects.keys()
            for f_key in total_key_list:
                if len(aim_objects[f_key].nodes) != 1:
                    continue
                key_list.append(f_key)
            return key_list

        def get_node_info(aim_object, set_name):

            aim_node = aim_object[set_name].nodes[0]
            node_coord = aim_node.coordinates
            # node_label = int(aim_node.label)  # 暂时不用label
            return [set_name, node_coord[0], node_coord[1]]

        def check_single_element_object(aim_objects):
            """
            return key_list
            """
            key_list = []
            total_key_list = aim_objects.keys()
            for f_key in total_key_list:
                if len(aim_objects[f_key].elements) != 1:
                    continue
                key_list.append(f_key)
            return key_list

        def get_element_info(aim_object, set_name, n_id_list, n_coord_list):

            aim_element = aim_object[set_name].elements[0]
            element_connect = aim_element.connectivity
            # element_label = int(aim_element.label)  # 暂时不用label
            
            if len(element_connect) != 4:
                raise TypeError("Odb process Error, only support rectange mesh type!(4)")
            
            p1_coord = n_coord_list[n_id_list.index(element_connect[0])]
            p2_coord = n_coord_list[n_id_list.index(element_connect[1])]
            p3_coord = n_coord_list[n_id_list.index(element_connect[2])]
            p4_coord = n_coord_list[n_id_list.index(element_connect[3])]
            
            # 计算形心
            Gx, Gy = calculate_element_centrol(\
                p1_coord, p2_coord, p3_coord, p4_coord)

            return [set_name, Gx, Gy]

        def calculate_element_centrol(p1_c, p2_c, p3_c, p4_c):

            x1 = p1_c[0]
            y1 = p1_c[1]
            x2 = p2_c[0]
            y2 = p2_c[1]
            x3 = p3_c[0]
            y3 = p3_c[1]
            x4 = p4_c[0]
            y4 = p4_c[1]

            area1 = abs((x1*y2+x2*y3+x3*y1) - (y1*x2+y2*x3+y3*x1))*0.5
            area2 = abs((x1*y3+x3*y4+x4*y1) - (y1*x3+y3*x4+y4*x1))*0.5

            G1x = (x1 + x2 + x3)/3.0
            G1y = (y1 + y2 + y3)/3.0
            G2x = (x1 + x3 + x4)/3.0
            G2y = (y1 + y2 + y4)/3.0

            Gx = (area1*G1x + area2*G2x)/(area1 + area2)
            Gy = (area1*G1y + area2*G2y)/(area1 + area2)

            return Gx, Gy

        # <data>
        set_name_list = []  # [[], [], [], ...]
        x_loc_list = []
        y_loc_list = []

        # 1 对于可能涉及的节点集 (通过对象是否唯一判断)
        # 1.1 intance1-soil
        node_set_object_1 = self.__aim_instance.nodeSets
        node_set_name_list1 = check_single_node_object(node_set_object_1)

        for set_name in node_set_name_list1:
            tl = get_node_info(node_set_object_1, set_name)
            set_name_list.append(tl[0])
            x_loc_list.append(tl[1])
            y_loc_list.append(tl[2])

        # 1.2 instance2-wall-zc
        node_set_object_2 = self.__aim_instance2.nodeSets
        node_set_name_list2 = check_single_node_object(node_set_object_2)

        for set_name in node_set_name_list2:
            tl = get_node_info(node_set_object_2, set_name)
            set_name_list.append(tl[0])
            x_loc_list.append(tl[1])
            y_loc_list.append(tl[2])
        
        # 1.3 instance3-chenqi
        node_set_object_3 = self.__aim_instance3.nodeSets
        node_set_name_list3 = check_single_node_object(node_set_object_3)

        for set_name in node_set_name_list3:
            tl = get_node_info(node_set_object_3, set_name)
            set_name_list.append(tl[0])
            x_loc_list.append(tl[1])
            y_loc_list.append(tl[2])

#        # 2 对于可能涉及的单元集
#        element_set_object_1 = self.__aim_instance.elementSets
#        ele_set_name_list1 = check_single_element_object(element_set_object_1)
#        # 必须先把所有的节点ID和节点坐标先都获取了
#        n_id_list, n_coord_list = get_all_nodes_info(self.__aim_instance)
#        for set_name in ele_set_name_list1:
#            tl = get_element_info(\
#                element_set_object_1, set_name, n_id_list, n_coord_list)
#            set_name_list.append(tl[0])
#            x_loc_list.append(tl[1])
#            y_loc_list.append(tl[2])

        # 3 获取隧道中点坐标
        top_side_name = "TUNNEL_1_TOP"  # 前面模型不要改名称，如果修改了，这里必须匹配
        down_side_name = "TUNNEL_5_BOTTOM"
        left_side_name = "TUNNEL_7_LEFT"
        right_side_name = "TUNNEL_3_RIGHT"

        top_y_loc = y_loc_list[set_name_list.index(top_side_name)]
        bottom_y_loc = y_loc_list[set_name_list.index(down_side_name)]
        left_x_loc = x_loc_list[set_name_list.index(left_side_name)]
        right_x_loc = x_loc_list[set_name_list.index(right_side_name)]

        centrol_x = (left_x_loc + right_x_loc)*0.5
        centrol_y = (top_y_loc + bottom_y_loc)*0.5

        # 4 转换坐标系，使隧道中点位于原点
        f_x_loc_list = [ite-centrol_x for ite in x_loc_list]
        f_y_loc_list = [ite-centrol_y for ite in y_loc_list]

        # 5 总列表
        f_row_data = [["set_name", "x_loc", "y_loc"]]
        for k in range(len(set_name_list)):
            f_row_data.append([\
                set_name_list[k], f_x_loc_list[k], f_y_loc_list[k]])

        # 6 输出csv
        self.__csv_out_row("coordData", f_row_data)

def odb_process_api(zjnt_pressure):

    # 1 get odb name list
    odb_name_list = get_odb_name_list()

    # 2 for each odb
    final_u1_list = []
    final_time_list = []
    for k in range(len(odb_name_list)):
        print("\nOdb process on {A}/{B} || {C}"\
            .format(A=k+1, B=len(odb_name_list), C=odb_name_list[k]))

        OP = odbProcess()
        OP.odb_name = odb_name_list[k]

        # odb open status check
        f_status = OP.get_abaqus_object()
        if not f_status:
            final_u1_list.append(None)
            final_time_list.append(None)

        else:
            # 1 <历程输出> 系列用户指定，(注：单元集和节点集的控制均在csv输出这里)
            # final_u1, final_time = OP.user_define_hist_process_by_session()  # 历史版本
            # final_u1, final_time = OP.user_define_hist_process()  # 历史版本
            final_u1, final_time = OP.user_define_field_process_for_monitor()  # 补丁

            # TODO python字典的键是唯一的，会被覆盖，所以存在问题，全部按照场变量输出的形式重做

            # 2 <场输出> zjnt面积
            OP.zjnt_ele_node_info()  # zjnt预处理：先获取单元集与节点集合对应关系
            OP.user_define_field_process()

            # 3 <坐标输出> 历程输出对应的节点集和单元集，同时转换坐标系
            OP.user_define_coord_process_v1()  # TODO

            final_u1_list.append(final_u1)
            final_time_list.append(final_time)

            # close odb
            OP.odb_close()

    # 3 print输出 u1 || zjnt压回去的距离 || 当前压强
    for k in range(len(odb_name_list)):

        # 计算zjnt当前压强值  <注意> 分析步时间和数量调整时，必须修改此处 (2.0是第三个分析步开始时间, 1.0是第三个分析步的总时间)
        if final_time_list[k] is None:
            continue
        # pressure_now = zjnt_pressure*(final_time_list[k]-2.0)/(1.0)
        pressure_now = zjnt_pressure*final_time_list[k]/(1.0)

        print("{A} || final u1 = {B} || final pressure = {C} || total pressure = {D}"\
            .format(A=odb_name_list[k], B=final_u1_list[k], C=pressure_now,
                D=zjnt_pressure))


if __name__=="__main__":

    print("\nProgram start")

    odb_process_api(zjnt_pressure=-2000000.0)

    print("\nProgram end")
