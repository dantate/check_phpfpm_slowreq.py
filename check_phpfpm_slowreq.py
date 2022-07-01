#!/usr/bin/python3 -O
""" Check php_status page for slow requests and report back.  Internal use. (c) 2022 Daniel Tate v1.0 \
build 4
"""

import argparse
import urllib.request
import json
import urllib
import shutil
import os
from time import perf_counter
from datetime import datetime
from datetime import timedelta
from os.path import exists

tmp_dir = "/tmp/phpfpm_diff"

differential_dir = tmp_dir + "/"

user_agent = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'

parser = argparse.ArgumentParser()
parser.add_argument('-c', '--crit', help="crit threshold", metavar="crit", type=int)
parser.add_argument('-w', '--warn', help="warn threshold", metavar="warn", type=int)
parser.add_argument('-s', '--site', help="warn threshold", metavar="warn", type=str)
parser.add_argument('-d', '--diff', help="Differential Mode", action='store_true')
parser.add_argument('-t', '--time', help="Time", metavar="time", type=int, choices=[30, 60, 90, 120])
args = parser.parse_args()

def get_status ():
    if __debug__:print(f"Got site as {args.site}")
    url = args.site
    headers={'User-Agent':user_agent,}

    request=urllib.request.Request(url,None,headers)
    response=urllib.request.urlopen(request)
    data = response.read()
    return(data)

def process_json (data_in):
   json_dict = json.loads(data_in)
   if __debug__: print (json_dict)
   return(json_dict['slow requests'])

def file_age (file, delta):
    cutoff = datetime.utcnow() - delta
    mtime = datetime.utcfromtimestamp(os.path.getmtime(file))
    if mtime < cutoff:
        return True
    return False

def touch(fname, times=None):
    with open(fname, 'a'):
        os.utime(fname, times)

def get_aged_reqs (difffile):
    if __debug__: print("DEBUG: SUB: get_aged_reqs")
    with open(difffile, 'r') as dfile:
        lines = dfile.readlines()
        for line in lines:
            my_list=line.split()
            reqcount=my_list[1]
            if __debug__:
                print("DEBUG: SUB: aged_reqs: my_list: ",my_list)
                print("DEBUG: SUB: aged_reqs: reqcount: ",reqcount)
            dfile.close()
            return reqcount

def rotate():
    if __debug__: print(f"DEBUG: DIFF: ROTATE: File 00m is {args.time} minutes old")
    os.replace(differential_dir + "90m", differential_dir + "120m")
    os.replace(differential_dir + "60m", differential_dir + "90m")
    os.replace(differential_dir + "30m", differential_dir + "60m")
    os.replace(differential_dir + "00m", differential_dir + "30m")
    if __debug__: print("DEBUG: DIFF: POSTROTATE: Creating new datafile...")
    with open(differential_dir + "00m", 'w') as f00m:
        str_assemble1 = str(perf_counter())
        str_assemble2 = str(str(slow_req))
        str_assemble = str_assemble1 + " " + str_assemble2
        test = f00m.write(str_assemble)
        if __debug__: print("DEBUG: DIFF: POSTROTATE: New Create is:", test)
        f00m.close()

def setup_env ():
    mkdir = os.makedirs(differential_dir)
    if __debug__:
        print("DEBUG: DIFF: mkdir: ", mkdir)
        print("DEBUG: DIFF: Creating initial file")
    with open(differential_dir + "00m", 'w') as f00m:
        str_assemble1 = str(perf_counter())
        str_assemble2 = str(str(slow_req))
        str_assemble = str_assemble1 + " " + str_assemble2
        write = f00m.write(str(str_assemble))
        if __debug__: print("DEBUG: DIFF: write is", write)
        f00m.close()
        shutil.copy(differential_dir + "00m", differential_dir + "30m")
        shutil.copy(differential_dir + "00m", differential_dir + "60m")
        shutil.copy(differential_dir + "00m", differential_dir + "90m")
        shutil.copy(differential_dir + "00m", differential_dir + "120m")

def validate_differential (old, new, current):
    old = int(old)
    new = int(new)
    current = int(current)
    if int(old) == slow_req:
            print(f"OK: Slow Reqs Unchanged {int(new)} new in {args.time} min ({current})|new_reqs={new};{args.warn};{args.crit}")
            exit(0)
    elif int(old) > slow_req:
        # 0 required here or else it skews the graphs with a huge negative drop.
            print(f"OK: Decrease in slow requests from {int(old)} to {current} |new_reqs=0;{args.warn};{args.crit}")
            exit(0)
    elif (old < args.warn):
            print(f"OK: {new} new slow requessts in {args.time} mins ({current})|new_reqs={new};{args.warn};{args.crit}")
            exit(0)
    elif (old >= args.warn and new < args.crit):
            print(f"WARNING: {new} new slow requests in {args.time} mins ({current})|new_reqs={new};{args.warn};{args.crit}")
            exit(1)
    else:
            print(f"CRITICAL: slow reqs: {new} new slow reqs in in {args.time} mins ({current})|new_reqs={new};{args.warn};{args.crit}")
            exit(2)

def validate_normal (reqs):
    if __debug__: print(f"DEBUG: Types: {type(args.warn)}, {type(reqs)}")
    if ( reqs < args.warn ):
        print('OK', reqs, "| slow_reqs=%d" %reqs)
        exit(0)

    elif ( reqs >= args.warn and reqs < args.crit ):
        print('WARN', reqs,"| slow_reqs=%d" %reqs)
        exit(1)
    else:
        print('CRITICAL', reqs,"| slow_reqs=%d" %reqs)
        exit(2)

if __debug__:
    print(f"DEBUG: warn: {args.warn} crit: {args.crit} elastic thresh: {args.diff} elastic time: \
{args.time}")

if __debug__:
    print("DEBUG: individual NONEs crit: ", args.crit is None,"warn: ", args.warn is None, "diff", args.diff is None)
    print("DEBUG: nested w/o diff", ((args.crit is None) or (args.warn is None)))
    print("DEBUG: nested w/ diff", (((args.crit is None) or (args.warn is None)) or args.diff is None))
    print(f"DEBUG: check_param: crit {args.crit} warn {args.warn} diff {args.diff}")

### Determine flags..

if (args.crit is not None) and (args.warn is not None):
    if __debug__: print(f"DEBUG: passed crit/warn validation")
    if args.diff is True:
        if __debug__: print(f"DEBUG: args.diff is True")
        normal_mode = 0
    else:
        if __debug__: print(f"DEBUG: args.diff is False, falling to normal mode")
        normal_mode = 1

if (args.diff and not args.time):
    print("You must specify time with differential.")
    exit(1)

if (args.time and not args.diff):
    print("You must specify differential with time.")

elif (args.crit is None) or (args.warn) is None:
  print(f"ERROR: you must specify crit and warn")
  exit(2)
elif (args.crit == args.warn):
    print(f"ERROR: warn and crit must be different values")
    exit(2)
elif args.warn > args.crit:
    print('warning level must be less than critical level')
    exit(2)

json_data = get_status()
slow_req = process_json(json_data)


# Detect if we are in differential mode.
if __debug__:print(f"DEBUG: DIFF: args.diff is True: {args.diff is True}")
if args.diff is True:
    if __debug__: print("DEBUG: DIFF: Differential is ON")

### Do Setup if Needed.

    dir_exists = os.path.exists(differential_dir)
    if __debug__: print(f"DEBUG: DIFF: dir_exists: {dir_exists}")
    if not dir_exists:
        setup_env()

if __debug__:
    print("DEBUG: normal mode is:", normal_mode)
    print("DEBUG: normal logic test is:", (normal_mode == 1))

### File Aging
if (normal_mode == 0):

    if __debug__:
        print(f"DEBUG: DIFF: DIFFERENTIAL")
        print(f"DEBUG: Aging...")
        print("DEBUG: DIFF: ROTATE: File 00m: ",file_age(differential_dir + "00m",timedelta(minutes=args.time)))
    if file_age(differential_dir + "00m",timedelta(minutes=args.time)):
        rotate() # will prv file w/ slow_reqs={log|wc-l}
        aged_reqs = get_aged_reqs(differential_dir + str(args.time) +"m")
        new_reqs = (slow_req - int(aged_reqs))
        validate_differential(aged_reqs,new_reqs,slow_req)

    else:
        if __debug__: print("DEBUG: DIFF: NOAGE: File is not yet aged out.")
        aged_reqs = get_aged_reqs(differential_dir + str(args.time) +"m")
        new_reqs = (slow_req - int(aged_reqs))
        validate_differential(aged_reqs,new_reqs,slow_req)

if (normal_mode == 1):
    if __debug__: print(f"In NORMAL MODE {normal_mode}")
    validate_normal(int(slow_req))

