#!/usr/bin/env python

from optparse import OptionParser
import math
import logging
import sys
import os.path
import subprocess
import errno

logger = logging.getLogger(__name__)

def execute(command, input = "", dry_run = False):
    """Spins off a subprocess to run the cgiven command"""
    logger.debug("Running: " + command)
   
    if not dry_run:
        proc = subprocess.Popen(command.split(), 
                                stdin = subprocess.PIPE, stdout = 2, stderr = 2)
        proc.communicate(input)
        if proc.returncode != 0: 
            raise Exception("Returns %i :: %s" %( proc.returncode, command ))

def mkdirp(*p):
    """Like mkdir -p"""
    path = os.path.join(*p)
         
    try:
        os.makedirs(path)
    except OSError as exc: 
        if exc.errno == errno.EEXIST:
            pass
        else: raise
    return path

if __name__ == "__main__":
    FORMAT = '%(asctime)-15s - %(levelname)s - %(message)s'
    logging.basicConfig(format=FORMAT, level=logging.DEBUG)
    
    parser = OptionParser()
    parser.set_usage("""%prog [options] <task_list> <chunk_size> <walltime> 
    eg.     %prog jobs 50 03:00:00
""")        
    parser.add_option("-n", dest="dry_run",
        action="store_true", default=False,
        help="Dry run.  No commands are executed, but script files are generated.")
    parser.add_option("--processes", dest="processes",
        default=8, type="int", 
        help="Number of processes to parallelize over.")
    parser.add_option("--output_dir", dest="output_dir",
        default="output", type="string", 
        help="Path to output folder")
    parser.add_option("--logs_dir", dest="logs_dir",
        default="logs", type="string", 
        help="Path to logs folder")
    options, args = parser.parse_args()
    
    if len(args) != 3: 
        parser.error("Unexpected number of arguments.")


    task_list_name = args[0]
    chunk_size     = int(args[1]) 
    walltime       = args[2]
    task_list      = open(task_list_name).readlines()
    num_jobs       = int(math.ceil(len(task_list) / float(chunk_size)))

    qsub_options = ['-l nodes=1:ppn=%i,walltime=%s' % (options.processes, walltime), 
                    '-j oe',
                    '-o %s' % options.logs_dir,
                    '-V'] 
    
    mkdirp('.scripts')
    for chunk in range(num_jobs):
        scriptfile=".scripts/%s_%i.sh" % (task_list_name, chunk)
        script = open(scriptfile, "w") 
    
        script.write("#!/bin/bash\n")

        for opt in qsub_options: 
            script.write("#PBS %s\n" % opt)

        script.write("cd $PBS_O_WORKDIR\n") 
        script.write("parallel -j%i <<TASKS\n" % options.processes) 
        script.writelines(task_list[chunk*chunk_size:chunk*chunk_size+chunk_size])
        script.write("TASKS\n") 
        script.close()

        execute("chmod +x %s" % scriptfile)
        execute("qsub %s" % scriptfile, dry_run = options.dry_run)