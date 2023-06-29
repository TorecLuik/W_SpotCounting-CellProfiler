import sys
import os
from cytomine.models import Job
from subprocess import run
from biaflows import CLASS_SPTCNT
from biaflows.helpers import BiaflowsJob, prepare_data, upload_data, upload_metrics
import json


def parse_cellprofiler_parameters(bj, pipeline, tmpdir):
    """
    Naive implementation that parses parameters from commandline 
    and descriptor.json
    and writes those to the cellprofiler pipeline file.
    
    This implementation uses the descriptor.json 'name' field to match 
    with the pipeline.
    
    Note that this works incorrectly when multiple of the same cellprofiler
    modules are used in a pipeline. It will override all options then.
    
    TODO: add a way to match descriptor.json param to the correct module in cp.
    """
    print(bj.__dict__, pipeline, tmpdir)
    
    # read params from descriptor.json
    with open("/app/descriptor.json", "r") as file:
        software_desc = json.load(file)
        if software_desc is None or "inputs" not in software_desc:
            raise ValueError("Cannot read 'descriptor.json' or missing 'inputs' in JSON")
        descriptor_params = [p for p in software_desc["inputs"] 
                             if not p['id'].startswith("cytomine")]

    cpparams = {}
    for param in descriptor_params:
        cpparams[param['name']] = param['id']

    mod_pipeline = os.path.join(tmpdir, os.path.basename(pipeline))
    rhdl = open(pipeline)
    whdl = open(mod_pipeline, "w")
    for line in rhdl:
        ar = line.split(":")
        if ar[0].strip() in cpparams.keys():
            new_line = ar[0] + ":" + \
                str(getattr(bj.parameters, cpparams[ar[0].strip()]))+"\n"
            print("Adjust {} to {}".format(line, new_line))
        else:
            new_line = line
        whdl.write(new_line)

    return mod_pipeline


def main(argv):
    base_path = "{}".format(os.getenv("HOME"))  # Mandatory for Singularity
    problem_cls = CLASS_SPTCNT

    with BiaflowsJob.from_cli(argv) as bj:
        bj.job.update(status=Job.RUNNING, progress=0,
                      statusComment="Initialisation...")
        # 1. Prepare data for workflow
        in_imgs, gt_imgs, in_path, gt_path, out_path, tmp_path = prepare_data(
            problem_cls, bj, is_2d=True, **bj.flags)

        pipeline = "/app/PLA-dot-counting-with-speckle-enhancement.cppipe"

        # 2. Run CellProfiler pipeline
        bj.job.update(progress=25, statusComment="Launching workflow...")
        
        ## If we want to allow parameters, we have to parse them into the pipeline here
        # mod_pipeline = parse_cellprofiler_parameters(bj, pipeline, tmp_path)
        mod_pipeline = pipeline

        shArgs = [
            "cellprofiler", "-c", "-r", "-p", mod_pipeline,
            "-i", in_path, "-o", out_path, "-t", tmp_path,
        ]
        status = run(" ".join(shArgs), shell=True)

        if status.returncode != 0:
            err_desc = "Failed to execute the CellProfiler pipeline: {} (return code: {})".format(
                " ".join(shArgs), status.returncode)
            bj.job.update(progress=50, statusComment=err_desc)
            raise ValueError(err_desc)

        # 3. Upload data to BIAFLOWS
        upload_data(problem_cls, bj, in_imgs, out_path, **bj.flags, monitor_params={
            "start": 60, "end": 90, "period": 0.1,
            "prefix": "Extracting and uploading polygons from masks"})

        # 4. Compute and upload metrics
        bj.job.update(
            progress=90, statusComment="Computing and uploading metrics...")
        upload_metrics(problem_cls, bj, in_imgs, gt_path,
                       out_path, tmp_path, **bj.flags)

        # 5. Pipeline finished
        bj.job.update(progress=100, status=Job.TERMINATED,
                      status_comment="Finished.")


if __name__ == "__main__":
    main(sys.argv[1:])
