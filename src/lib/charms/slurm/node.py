import subprocess
import sys
import re

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
def get_inventory():
    info = subprocess.check_output("slurmd -C", shell=True).strip().decode('ascii')
    regex = re.compile(r"\b(\w+)\s*=\s*([^=]*)(?=\s+\w+\s*=|$)")
    inv = dict(regex.findall(info))
    return inv
