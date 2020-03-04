import subprocess
import sys
import re
import os.path
#Regex explanation:
#  \b           # Start at a word boundary
#  (\w+)        # Match and capture a single word (1+ alnum characters)
#  \s*=\s*      # Match a equal, optionally surrounded by whitespace
#  ([^=]*)      # Match any number of non-equal characters
#  (?=          # Make sure that we stop when the following can be matched:
#   \s+\w+\s*=  #  the next dictionary key
#  |            # or
#  $            #  the end of the string
#  )            # End of lookahead
def _get_inv():
    info = subprocess.check_output("slurmd -C", shell=True).strip().decode('ascii')
    regex = re.compile(r"\b(\w+)\s*=\s*([^=]*)(?=\s+\w+\s*=|$)")
    inv = dict(regex.findall(info))
    return inv

#Get the number of GPUs and check that they exist at /dev/nvidiaX
def _get_gpu():
    gpu = int(subprocess.check_output("lspci | grep -i nvidia | awk '{print $1}' | cut -d : -f 1 | sort -u | wc -l", shell=True))

    for i in range(gpu):
        gpu_path = "/dev/nvidia" + str(i)
        if not os.path.exists(gpu_path):
            return 0
    return gpu

def get_inventory():
    inv = _get_inv()
    inv['gpus'] = _get_gpu()
    return inv
