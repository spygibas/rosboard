#!/usr/bin/env python3

import psutil
import select
import subprocess
import time
import threading
import traceback

def mean(list):
    return sum(list)/len(list)

class SystemStatsSubscriber(object):
    GPU_NONE = 0
    GPU_NVIDIA = 1
    GPU_NVIDIA_EMBEDDED = 2

    def __init__(self, callback):
        self.callback = callback
        self.process = None
        self.gpu_type = SystemStatsSubscriber.GPU_NONE

        threading.Thread(target = self.start, daemon = True).start()

    def __del__(self):
        if self.process:
            self.process.terminate()
            self.process = None

    def unregister(self):
        if self.process:
            self.process.terminate()
            self.process = None

    def start(self):
        try:
            p = psutil.Process()
            
            while True:
                with p.oneshot():
                    sensors_temperatures = psutil.sensors_temperatures()
                    if 'coretemp' in sensors_temperatures:
                        cpu_coretemp = mean(list(map(lambda x:x.current, sensors_temperatures['coretemp'])))
                    
                    cpu_usage = mean(psutil.cpu_percent(percpu=True))
                    disk_usage = psutil.disk_usage('/').percent
                    net_bytes_sent = psutil.net_io_counters().bytes_sent
                    net_bytes_recv = psutil.net_io_counters().bytes_recv
                    mem_usage_virtual = psutil.virtual_memory().percent
                    mem_usage_swap = psutil.swap_memory().percent
                    
        except:
            traceback.print_exc()

    def check_gpu_type(self):
        try:
            subprocess.Popen(['nvidia-smi', '--help']).communicate()
            self.gpu_type = SystemStatsSubscriber.GPU_NVIDIA
        except FileNotFoundError:
            pass

        try:
            subprocess.Popen(['tegrastats', '--help']).communicate()
            self.gpu_type = SystemStatsSubscriber.GPU_NVIDIA_EMBEDDED
        except FileNotFoundError:
            pass

    def get_gpu(self):
        if self.gpu_type == SystemStatsSubscriber.GPU_NONE:
           return {"temp": 0, "power_draw": 0, "power_state": 0, "gpu_percent": 0}

        elif self.gpu_type == SystemStatsSubscriber.GPU_NVIDIA:
            nvinfo =  subprocess.Popen(['nvidia-smi', '-q', '-x'], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()

            try:
                for line in nvinfo[0].decode().split('\n'):
                    if '<gpu_temp>' in line and ' C' in line:
                        gpu_temp = float(re.search('<gpu_temp>(.*) C</gpu_temp>', line).group(1))
                    if '<power_draw>' in line and ' W' in line:
                        gpu_power_draw = float(re.search('<power_draw>(.*) W</power_draw>', line).group(1))
                    if '<power_state>' in line:
                        gpu_power_state = str(re.search('<power_state>(.*)</power_state>', line).group(1))
                    if '<gpu_util>' in line and ' %' in line:
                        gpu_util = float(re.search('<gpu_util>(.*) %</gpu_util>', line).group(1))
            except (AttributeError, ValueError) as e:
                    print("error updating gpu statistics")
        
            return {"temp": gpu_temp, "power_draw": gpu_power_draw, "power_state": gpu_power_state, "gpu_percent": gpu_util}
        
        elif self.gpu_type == SystemStatsSubscriber.GPU_NVIDIA_EMBEDDED:
            tegrastats =  subprocess.Popen(['timeout', '2s', 'tegrastats'], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
            return {"temp": 0, "power_draw": 0, "power_state": 0, "gpu_percent": 0}




if __name__ == "__main__":
    # Run test
    SystemStatsSubscriber(lambda msg: print("Received msg: %s" % msg))
    time.sleep(100)
