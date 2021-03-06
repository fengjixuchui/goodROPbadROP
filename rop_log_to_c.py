from sets import Set
import argparse
import json
from utils import *
import random

parser = argparse.ArgumentParser()
parser.add_argument("--roplog", help="all the rops founded by ROPgadget")
parser.add_argument("--config", help="a json file contain the desire Init and Goal state")
parser.add_argument("--coutput", help="the output c program")
parser.add_argument("--use_cfi", help="the output c program")
args = parser.parse_args()

with open(args.config) as f:
    config = json.load(f)

in_file = args.roplog
out_file = args.coutput

pruned = []
config["implemented"] = ["ret", "pop", "inc", "mov", "xor", "push"]
config["registers"] = ["eax", "ebx", "ecx", "edx"]

config["blacklist"] = ["ebp", "esi", "edi", "al", "ah", "bh", "bl", "cl", "ch", "cs", "dl", "ds", "dh", "es", "ss", "byte", "0x", " + ", "gs:" , "[0]"] #if you need to blacklist things

random.seed(config["seed"])
cfi = config["cfi"]
use_cfi = int(args.use_cfi)
print "Use CFI:", args.use_cfi

function_def_block = ""
switch_block = ""

with open(in_file) as f:
    pruned = []
    data = f.readlines()
    for l in data:
        if l.startswith("0") and l.endswith("ret\n"):
            _ = l.strip().split(" : ")
            address = _[0]
            gadget = _[1]
            if check_gadget(gadget, config):
                pruned.append([address, gadget])
    gadget_set = Set()
    for i in range(len(pruned)):
        gadget_name = "gadget_"+str(len(gadget_set))
        block = gadget_to_c(gadget_set, pruned[i][1], gadget_name)
        function_def_block+= block

    
for i in range(len(gadget_set)):
    gadget_name = "gadget_"+str(i)
    # sprinkle edges into the block
    # no_of_prev = random.randint(0, len(gadget_set)-1)
    if str(i) in cfi:
    	possible_prev = cfi[str(i)]
    else:
    	possible_prev = [random.randint(0, len(gadget_set)-1)]
    safe_guard = ""
    for p in possible_prev:
        safe_guard+="prev_choice == %d || "%p
    safe_guard = safe_guard[:-3]
    # print safe_guard

    if use_cfi==0:
        switch_block += """
        \tif(choice==%s){
        \t\tprintf("%s \\n");
        \t\t//assume(%s);
        \t\t%s();
        \t}\n"""%(i, i, safe_guard, gadget_name)

    else:
        switch_block += """
        \tif(choice==%s){
        \t\tif(%s){
        \t\t\tprintf("%s \\n");
        \t\t\t%s();
        \t\t}else{
        \t\t\treturn 0;
        \t\t}
        \t}\n"""%(i, safe_guard, i, gadget_name)

Init_block = build_Init_block(config)

main_header = \
'int main(){\n\
\tint choice = 0;\n\
\tint prev_choice = nd();\n\
\n\
\tprint_state();\n\
\t//bounded\n\
\tfor(int i =0; i< 10; i++){\n\
\t\tchoice = nd();\n\
\t\tassume(choice>=0 && choice<%s);\n\
'%len(gadget_set)




sassert = build_sassert(config)

main_tail = \
'\t\tprint_state();\n\
\t\t%s;\n\
\t\tprev_choice = choice;\n\
\t}\n \
\treturn 0;\n\
}'%sassert

head_file = open("head.c", "r")
ls = head_file.readlines()
with open(out_file, "w") as output:
    output.write(ls[0])
    output.write(ls[1])
    output.write(Init_block)
    for l in ls[2:]:
        output.write(l)
    output.write(function_def_block)
    output.write(main_header)
    output.write(switch_block)
    output.write(main_tail)
