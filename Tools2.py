#- * -coding: UTF-8- * -
# chenhongcheng3097@163.com
# 2025-7-22 v1  XY238
# 2025-8-28 v2  XY238
# 2025-10-23 v3  XY238

"""
注意：如果分析步时间、U1判定条件有修改，必须修改monitor_tools3_status_check函数中对应的值
"""

from abaqus import *
from abaqusConstants import *
from jobMessage import *
import job
import time
import subprocess
import visualization


def get_input_file():

    input_file_name = []
    for ite in os.listdir(os.getcwd()):
        if ite.endswith(".inp"):
            input_file_name.append(ite[:-4])

    return input_file_name


def monitor_tools1_command(command_content):

    os.system(command_content)
    return None


def monitor_tools2_command_and_return(command_content):

    try:
        return_result = os.popen(command_content).read()
    except Exception as ex:
        return_result = str(ex)

    return return_result


def monitor_tools3_status_check(time_now, monitor_data):
    """
    修改参数 dBUG here
    : monitor_status: 可选择是否执行强制中断
    """
    # check if already complete
    pross_list  = monitor_tools2_command_and_return("tasklist")
    if "standard.exe" not in pross_list:
        print("\nprogram probably end!")
        return None

    # check process
    if time_now >= 2.0:  # 地应力平衡时间1.0，kw分析步时间1.0，所以是2.0开始判断
        if monitor_data > 0.1:  # 正常情况，随着开挖的进行，向x轴负半轴移动，通过zjnt加压，向右挤，挤压回0.1mm的时候强制中断
            print("IN")
            monitor_tools1_command("taskkill /f /t /im standard.exe")
            time.sleep(5)


def job_monitor_set(inp_file_path, dof, node_set_name):
    
    try:
        with open(inp_file_path, 'r') as readFile:
            lines = readFile.readlines()
        
        final_lines = []
        for line in lines:
            if "*End Step" in line:
                final_lines.append("*Monitor, dof={A}, node={B}, frequency=1\n*End Step\n"\
                    .format(A=dof, B=node_set_name))
            else:
                final_lines.append(line)
        
        with open(inp_file_path, 'w') as writeFile:
            writeFile.writelines(final_lines)
    except:
        raise TypeError("\nTools2 || job_monitor_set error, pls check")


def onMessage(jobName, messageType, aim_data, userData=None):
    
    # print(dir(aim_data))
    # 执行作业监控，如果不存在value对象则跳过
    try:
        scrtipy_monitor_data = aim_data.value
        time_now = aim_data.time
        print("scrtipy_monitor_data = {}".format(scrtipy_monitor_data))
        monitor_tools3_status_check(time_now, scrtipy_monitor_data)
    except:
        pass
    
    if messageType == JOB_COMPLETED or messageType == JOB_ABORTED:

        monitorManager.removeMessageCallback(\
            jobName, messageType=messageType, callback=onMessage,
            userData=None)


def job_process_with_monitor(jobName, inpName, num_Cpu, num_Gpu):

    myJob = mdb.JobFromInputFile(name=jobName, inputFileName = 
        inpName, numCpus=num_Cpu, numDomains=num_Cpu, 
        numGPUs=num_Gpu)

    if  myJob.status == None:

        t0 = time.time()

        monitorManager.addMessageCallback(\
            jobName=jobName,
            messageType=ANY_MESSAGE_TYPE, 
            callback=onMessage,
            userData=None)

        myJob.submit()
        myJob.waitForCompletion()

        time.sleep(3)
        endTime = time.time()-t0

    return endTime


def job_process_api(monitor_dof=1, node_set_name="chenqi-1.hist_out_left",
    cpu_nums=8, gpu_nums=24):

    input_file_name = get_input_file()
    print(input_file_name)

    # for each inp
    for i in range(len(input_file_name)):
        print("\nJob process on {A}/{B}"\
            .format(A=i+1, B=len(input_file_name)))
        inp_name = input_file_name[i]

        # 设置监听 
        job_monitor_set("{}.inp".format(inp_name), dof=monitor_dof, \
            node_set_name=node_set_name)

        # 提交作业 || 带监听
        process_time = job_process_with_monitor(inp_name, inp_name, cpu_nums, gpu_nums)
        print("\nJob {A} process time = {B}"\
            .format(A=inp_name, B=process_time))


if __name__=="__main__":

    print("\nProgram start")

    job_process_api(monitor_dof=1, node_set_name="chenqi-1.Tunnel_7_left",
        cpu_nums=8, gpu_nums=24)

    print("\nProgram end")
