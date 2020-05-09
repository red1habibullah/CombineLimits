import os
import logging
import random
import errno
import subprocess
import argparse

import ROOT

ROOT.gROOT.SetBatch()


# helper functions
def python_mkdir(dir):
    '''A function to make a unix directory as well as subdirectories'''
    try:
        os.makedirs(dir)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(dir):
            pass
        else: raise

def runCommand(command):
    return subprocess.Popen(command,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT).communicate()[0]


logging.basicConfig(format='%(asctime)s.%(msecs)03d %(levelname)s %(name)s: %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')


parser = argparse.ArgumentParser(description='Prepare grid submission')
parser.add_argument('jobname',type=str,help='Job name for submission')
parser.add_argument('--crab',action='store_true',help='Prepare crab submission (otherwise does condor assuming UW Madison)')
parser.add_argument('--site',type=str,default='T2_US_Wisconsin',help='Site for storage')
parser.add_argument('--hmasses',type=int,default=[125,300,750],nargs='+',help='H masses to run')
parser.add_argument('--moderanges',type=str,default=['lowmass','upsilon','highmass'],choices=['lowmass','upsilon','highmass'],nargs='+',help='A mass ranges to run')
parser.add_argument('--toys',type=int,default=2000,help='Number of toys')
parser.add_argument('--toysPerJob',type=int,default=100,help='Number of toys per job')
parser.add_argument('--testing',action='store_true',help='Test does one point per mode')
parser.add_argument('--verbose',action='store_true',help='Run combine with verbose')
parser.add_argument('--convert',action='store_true',help='Only convert')
parser.add_argument('--reduced',action='store_true',help='Reduced h/a grid for large statistics')

args = parser.parse_args()

user = os.environ['USER']
site = args.site
store = '/store/user/{}'.format(user)
hdfs = '/hdfs/store/user/{}'.format(user)
doCrab = args.crab
testing = args.testing
convertOnly = args.convert
reduced = args.reduced
verbose = args.verbose

jobname = args.jobname
if doCrab:
    jobname = 'crab_' + jobname
if testing:
    jobname = 'test_' + jobname


hmasses = args.hmasses
amasses = [x*.1 for x in range(36,210,1)] + [21.0]
lowmass_amasses = amasses
upsilon_amasses = amasses
highmass_amasses = amasses
if reduced:
    lowmass_amasses = [x*.1 for x in range(36,42,2)] + [x*.1 for x in range(45,90,5)]
    upsilon_amasses = [x*.1 for x in range(80,115,2)] + [11.5]
    highmass_amasses = [11.0, 11.5] + [x*.1 for x in range(120,220,10)]
if testing:
    amasses = [7.0,9.0,15.0]
    lowmass_amasses = [7.0]
    upsilon_amasses = [9.0]
    highmass_amasses = [15.0]


#mode = 'mmmt_mm_h_parametric_unbinned_with1DFits'
#mode = 'mmmt_mm_h_parametric_unbinned_{moderange}With1DFits'
mode = 'mmmt_mm_h_parametric_unbinned_{moderange}With1DFitsDoubleExpo'
#toys = 5000 # reasonable amount for all points is 100 per job, longest right now is upsilon 125, 12 hours
toys = args.toys

moderanges = args.moderanges
rangeMap = {
    'lowmass': [2.5,8.5],
    'upsilon': [7.5,12],
    'highmass': [11,25],
}

# use this for now, also support using results from asymptotic...
rMap = {
    125: [0.025,1.00],
    300: [0.050,2.00],
    750: [0.500,25.0],
}

altRMap = {
    125: [0.100,1.00],
    300: [0.100,1.00],
    750: [1.000,6.0],
}

drMap = {
    125: 0.025,
    300: 0.05,
    750: 0.5,
}

altDRMap = {
    125: 0.05,
    300: 0.1,
    750: 0.5,
}

if doCrab:
    #scratchdir = '/nfs_scratch/{}/crab_projects'.format(user)
    scratchdir = 'crab_projects'
else:
    scratchdir = '/nfs_scratch/{}/condor_projects'.format(user)

def submit_condor(ws,quartiles,mode,h,a):
    sample_dir = '{}/{}/{}/{}/{}'.format(scratchdir,jobname,mode,h,a)
    full_path = os.path.abspath(os.path.join(os.environ['CMSSW_BASE'],'src',ws))
    dsplit = full_path.split('/')
    srcpos = dsplit.index('src')
    drel = '/'.join(dsplit[srcpos:])
    dreldir = '/'.join(dsplit[srcpos:-1])

    # create submit dir
    submit_dir = '{}/submit'.format(sample_dir)
    if os.path.exists(submit_dir):
        logging.warning('Submission directory exists for {0}.'.format(jobname))
        return

    # setup the job parameters
    if quartiles:
        rmin = 0.5*min(quartiles)
        rmax = 1.2*max(quartiles)
    else:
        rmin = rMap[h][0] if a<8 else altRMap[h][0]
        rmax = rMap[h][1] if a<8 else altRMap[h][1]
    dr = drMap[h] if a<8 else altDRMap[h]
    num_points = int((rmax-rmin)/dr)
    points_per_job = 1
    toys_per_job = args.toysPerJob
    jobs_per_point = int(toys/toys_per_job)
    if jobs_per_point<1: jobs_per_point = 1

    # create dag dir
    dag_dir = '{}/dags/dag'.format(sample_dir)
    os.system('mkdir -p {0}'.format(os.path.dirname(dag_dir)))
    os.system('mkdir -p {0}'.format(dag_dir+'inputs'))

    # output dir
    output_dir = '/store/user/{}/{}/{}/{}/{}'.format(user, jobname, mode, h, a)

    # create file list
    rlist = [r*(rmax-rmin)/num_points + rmin for r in range(int(num_points/points_per_job))]
    input_name = '{}/rvalues.txt'.format(dag_dir+'inputs')
    with open(input_name,'w') as file:
        for r in rlist:
            for i in range(jobs_per_point):
                file.write('{}_{}\n'.format(r,i))

    # create bash script
    bash_name = '{}/{}.sh'.format(dag_dir+'inputs', jobname)
    bashScript = '#!/bin/bash\n'
    #bashScript += 'printenv\n'
    bashScript += 'read -d "_" -r RVAL < $INPUT\n'
    for i in range(points_per_job):
        dr = i*(rmax-rmin)/points_per_job
        bashScript += 'combine -M HybridNew -v {verbosity} -d $CMSSW_BASE/{ws} -m {h} --setParameters MA={a} --freezeParameters=MA --LHCmode LHC-limits --singlePoint $(bc -l <<< "$RVAL+{points}") --rMax 30 --saveToys --saveHybridResult -T {toys} -s -1 --clsAcc 0\n'.format(ws=drel,h=h,a=a,points=dr,toys=toys_per_job,jobname=jobname,verbosity=2 if verbose else -1)
    if points_per_job>1:
        bashScript += 'hadd $OUTPUT higgsCombine*HybridNew.mH{}*.root\n'.format(h)
        bashScript += 'rm higgsCombine*.root\n'.format(h)
    else:
        bashScript += 'mv higgsCombine*.root $OUTPUT\n'.format(h)
    with open(bash_name,'w') as file:
        file.write(bashScript)
    os.system('chmod +x {}'.format(bash_name))

    # create farmout command
    farmoutString = 'farmoutAnalysisJobs --infer-cmssw-path --fwklite --input-file-list={} --assume-input-files-exist'.format(input_name)
    farmoutString += ' --submit-dir={} --output-dag-file={} --output-dir={}'.format(submit_dir, dag_dir, output_dir)
    farmoutString += ' --extra-usercode-files="{}" {} {}'.format(dreldir, jobname, bash_name)

    print farmoutString

def submit_crab(ws,quartiles,mode,h,a):
    if quartiles:
        rmin = min(quartiles[:5])*0.5
        rmax = max(quartiles[:5])*1.2
    else:
        rmin = rMap[h][0] if a<8 else altRMap[h][0]
        rmax = rMap[h][1] if a<8 else altRMap[h][1]
    dr = drMap[h] if a<8 else altDRMap[h]
    num_points = int((rmax-rmin)/dr)
    points_per_job = 1
    toys_per_job = args.toysPerJob
    jobs_per_point = int(toys/toys_per_job)
    if jobs_per_point<1: jobs_per_point = 1

    # this will do multiple r values in a regular grid
    pointsString = '{:.3}:{:.3}:{:.3}'.format(rmin,rmax,dr)

    crab = 'custom_crab_{mode}_{h}_{a}.py'.format(mode=mode,h=h,a=a)

    # this will create multiple jobs for each point with the specified seed
    seedint = random.randint(1,123456)
    seeds = '{}:{}:{}'.format(seedint,seedint+jobs_per_point-1,1) if jobs_per_point>1 else str(seedint)

    # note: blacklist set Oct 31, 2019
    crabString = '''
def custom_crab(config):
    config.General.workArea = '{scratchdir}/{jobname}/{tag}/{h}/{a}'
    config.Data.outLFNDirBase = '/store/user/{user}/{jobname}/{tag}/{h}/{a}'
    config.Site.storageSite = '{site}'
    config.JobType.allowUndistributedCMSSW = True
    config.Site.blacklist = ['T3_KR_KNU', 'T3_FR_IPNL', 'T2_TR_METU', 'T2_TW_NCHC', 'T2_BE_IIHE', 'T3_US_Baylor']
'''.format(scratchdir=scratchdir, user=user, jobname=jobname, tag=mode, h=h, a=a, site=site)

    temp = 'temp_HybridNew_{h}'.format(h=h)
    with open('{temp}/{crab}'.format(temp=temp,crab=crab),'w') as f:
        f.write(crabString)

    command = 'combineTool.py -M HybridNew -v {verbosity} -d {ws} -m {h} --setParameters MA={a} --freezeParameters=MA --LHCmode LHC-limits --singlePoint {points} --rMax 30 --saveToys --saveHybridResult -T {toys} -s {seeds} --clsAcc 0 --job-mode crab3 --task-name {jobname} --custom-crab {crab}'.format(ws=ws,h=h,a=a,points=pointsString,toys=toys_per_job,jobname=jobname,seeds=seeds,crab=crab,verbosity=2 if verbose else -1)
    #command += ' --fullBToys'
    #command += ' --dry-run'
    print command




for moderange in moderanges:
    for h in hmasses:
        thismode = mode.format(moderange=moderange)
        datacard = 'datacards_shape/MuMuTauTau/{mode}_HToAAH{h}AX.txt'.format(mode=thismode,h=h)
        ws = '{mode}_{h}.root'.format(mode=thismode,h=h)
        temp = 'temp_HybridNew_{h}'.format(h=h)
        python_mkdir(temp)
        print 'text2workspace.py {datacard} -m {h} -o {temp}/{ws}'.format(datacard=datacard,h=h,temp=temp,ws=ws)
        if doCrab: print 'pushd {temp}'.format(temp=temp)
        prev_qs = []
        thisamasses = amasses
        if moderange=='lowmass':
            thisamasses = lowmass_amasses
        if moderange=='upsilon':
            thisamasses = upsilon_amasses
        if moderange=='highmass':
            thisamasses = highmass_amasses
        for a in thisamasses:
            if convertOnly: continue
            if a<rangeMap[moderange][0]: continue
            if a>rangeMap[moderange][1]: continue
            if a % 1 < 1e-10: astr = '{0:.0f}'.format(a)
            elif (10*a) % 1 < 1e-10: astr = '{0:.1f}'.format(a)
            elif (100*a) % 1 < 1e-10: astr = '{0:.2f}'.format(a)
            else: astr = 'HELP'

            qs = []
            # turn off for now
            #tfile = ROOT.TFile.Open('{hdfs}/{m}/{h}/higgsCombineHToAAH{h}A{a:.1f}_{m}.AsymptoticLimits.mH{h}.root'.format(hdfs=hdfs,h=h,a=a,m=thismode,astr=astr))
            #try:
            #    tree = tfile.Get("limit")
            #except:
            #    logging.error('Failed to open {} {} {}'.format(thismode,h,a))
            #    continue
            #for i, row in enumerate(tree):
            #    qs += [row.limit]
            #outline = ' '.join([str(x) for x in qs])
            #logging.info('{0}:{1}: Limits: {2}'.format(h,a,outline))

            #if not prev_qs: prev_qs = qs

            #if abs(qs[2]-prev_qs[2])/qs[2]>0.3:
            #    logging.info('{}:{}: Large jump in AsymptoticLimit, will use previous a mass limits for bounds'.format(h,a))
            #    qs = prev_qs

            #prev_qs = qs

            #if len(qs)<6:
            #    logging.info('{}:{}: Too few limits, will not sumbit'.format(h,a))
            #    continue

            if doCrab:
                submit_crab(ws,qs,thismode,h,a)
            else:
                submit_condor('{temp}/{ws}'.format(temp=temp,ws=ws),qs,thismode,h,a)

        if doCrab: print 'popd'

