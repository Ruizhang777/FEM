#- * -coding: UTF-8- * -
# chenhongcheng3097@163.com
# 2025-7-22 v1  XY238
# 2025-8-28 v2  XY238

from abaqus import *
from abaqusConstants import *
from textRepr import *
import itertools
import csv
from Tools1 import mdb_process_api
from Tools2 import job_process_api
from Tools3 import odb_process_api



def create_para_list(test_name_startswith, Ht_list, Lwt_list, We_list, He_ratio, Dcap_list,
    m_index_list):
    """
    根据参数列表，创建试验组
    """
    title_list = ["test_name", "m_index_list", 
        "Ht_list", "Lwt_list", "We_list", "He_ratio", "Dcap_list"]

    # 创建交互试验组 || 最终数据表的顺序，按此排列
    test_data_list = list(itertools.product(\
        m_index_list, Ht_list, Lwt_list, We_list, He_ratio, Dcap_list
        ))
    f_test_data_list = test_data_list

    # 创建试验名称列表
    test_name_list = []
    for i in range(len(f_test_data_list)):
        test_name = "{A}_{B}".format(A=test_name_startswith, B=i+1)
        test_name_list.append(test_name)

    return test_name_list, f_test_data_list, title_list


def user_define_input_para_form(real_data_list, F_Lct, F_Dt, F_tlining, F_Tw, F_Lc,
    material_data_group):
    """
    用户定义的输入文件清单
    注：real_data_list中的变量顺序与方法create_para_list中的变量顺序是一致的
    """
    title_list = ["test_name"]
    title_list.extend(["c", "E", "density", "fai", "xmu"])
    title_list.extend(["H_t", "H_e", "L_wt", "B", "Lct"])
    title_list.extend(["D_t", "t_linling", "T_w", "W_c", "L_c"])

    # <data>
    user_define_input_list = []

    # for each test group
    for ite_list in real_data_list:
        single_input_lits = []

        # 类别1 -- 土体属性
        mtl = material_data_group[ite_list[0]]
        single_input_lits.extend([\
            mtl[0], mtl[1], mtl[2], mtl[3], mtl[4]
            ])

        # 类别2 -- 几何与空间
        single_input_lits.extend([\
            ite_list[1], ite_list[4], ite_list[2], ite_list[3], F_Lct
            ])

        # 类别3 -- 结构与囊体
        single_input_lits.extend([\
            F_Dt, F_tlining, F_Tw, ite_list[5], F_Lc
            ])
        
        user_define_input_list.append(single_input_lits)
    
    return title_list, user_define_input_list


def tools_csv_output(csv_name, test_name_list, test_data_list, title_list):

    with open("{}.csv".format(csv_name), 'wb') as writeFile:
        csv_writer = csv.writer(writeFile)
        # title
        csv_writer.writerow(title_list)
        # value
        for i in range(len(test_name_list)):
            row_list = [test_name_list[i]]
            row_list.extend(test_data_list[i])
            csv_writer.writerow(row_list)


if __name__=="__main__":

    print("\nProgram start!")

    # <弹窗输入参数>
    input_para = getInputs((("Lct", "3.0")))

    # <1 用户修改参数>结构参数 || 用户提供图例从左往右
    We_list = [15.0, 45.0]  # 开挖半宽B
    He_ratio = [0.5, 2.0]  # 开挖深度是隧道顶部深度的XX倍
    Ht_list = [12.4, 37.2]
    Lwt_ratio = [0.5, 1.0]  # Lwt是He的XX倍
    Dcap_list = [0.2]  # 注浆囊体直径

    # <2 用户修改参数>固定单数
    F_Dt = 6.2  # 隧道外径
    F_Lct = float(input_para[0])  # 注浆囊体右侧离隧道左侧距离
    F_Tw=0.8  # 挡土墙宽度
    F_tlining=0.35  # 衬砌厚度
    F_Lc=8.0  # 胶囊高度

    # <3 用户修改参数>材料参数，Pa-m制【具体数据不参与交互数据】
    """
    材料参数列表按此排列：(1)粘聚力c、(2)模量E、(3)质量密度density、(4)摩擦角fai、(5)泊松比xmu
    每一个子列表，代表一组参数，组序号参与交互数据
    """
    material_data_group = [\
        [0.0, 9600000.0, 2039.4, 30.0, 0.3],
        [0.0, 21600000.0, 2039.4, 30.0, 0.3],
        [0.0, 3360000.0, 2039.4, 30.0, 0.3],
        [0.0, 3360000.0, 2039.4, 35.0, 0.3]
        ]
    material_index_list = [i for i in range(len(material_data_group))]
    # <4 其他控制参数>
    mesh_size = 0.5
    zjnt_pressure = -2000000.0
    step_zjnt_maxNumInc = 1000
    step_zjnt_minInc = 1e-5

    # 1 计算试验组参数
    test_name_list, test_data_list, title_list = create_para_list(\
        test_name_startswith="test",
        Ht_list=Ht_list,
        Lwt_list=Lwt_ratio,
        We_list=We_list,
        He_ratio=He_ratio,
        Dcap_list=Dcap_list,
        m_index_list=material_index_list
        )
    
    # 2 试验组参数判断 <Lwt必须大于Dt+Lct+Dcap>
    test_status_list = []
    for k in range(len(test_data_list)):
        test_data = test_data_list[k]
        
        # 判定参数
        Ht = test_data[1]
        He = test_data[4]*Ht
        Lwt = test_data[2]*He
        Dcap=test_data[5]
        
        # 判定条件1：如果注浆囊体位置与挡土墙位置冲突，则舍去
        if Lwt<F_Dt+F_Lct+Dcap:
            test_status_list.append(False)
        # 判定条件2：如果开挖深度超过40米，则舍去
        elif He>40.0:
            test_status_list.append(False)
        else:
            test_status_list.append(True)

#    # 3 实际交互参数写入csv表格 || dBUG
#    tools_csv_output("Para_list_for_dBUG", 
#        test_name_list, test_data_list, title_list
#        )

    # 4 根据用户要求，生成输出参数表格
    title_list, user_define_input_list = user_define_input_para_form(\
        test_data_list, F_Lct, F_Dt, F_tlining, F_Tw, F_Lc, material_data_group)

    # 5 用户定义交互参数写入csv表格
    tools_csv_output("Input_para_list", 
        test_name_list, user_define_input_list, title_list
        )

    # 6 MDB模块业务
    for k in range(len(test_name_list)):
        print("\nProcess on {A}/{B}"\
            .format(A=k+1, B=len(test_name_list)))
            
        # 排除试验组
        if not test_status_list[k]:
            continue

        test_name = test_name_list[k]
        test_data = test_data_list[k]
        material_list = material_data_group[test_data[0]]

        mdb_process_api(\
            test_name=test_name,
            F_Ht=test_data[1],
            F_Lwt_ratio=test_data[2],
            F_We=test_data[3],
            F_He_ratio=test_data[4],
            F_Dt=F_Dt,
            F_Lct=F_Lct,
            F_Dcap=test_data[5],
            F_Tw=F_Tw,
            F_tlining=F_tlining,
            F_Lc=F_Lc,
            soil_fai=material_list[3],
            soil_c=material_list[0],
            soil_E=material_list[1],
            soil_density=material_list[2],
            soil_xmu=material_list[4],
            mesh_size=mesh_size,
            zjnt_pressure=zjnt_pressure,
            step_zjnt_maxNumInc=step_zjnt_maxNumInc, 
            step_zjnt_minInc=step_zjnt_minInc
            )

    # 7 JOB模块业务 || monitor监控
    job_process_api(monitor_dof=1, node_set_name="chenqi-1.Tunnel_7_left",
        cpu_nums=48, gpu_nums=0)

    # 8 ODB模块业务
    odb_process_api(zjnt_pressure)

    print("\nProgram end!")

