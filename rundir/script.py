__author__ = 'jeanyves'

import os
import sys
import logging
import signal
import subprocess

DTIReg = "/tools/bin_linux64/DTI-Reg"
fiberprocess = "/tools/bin_linux64/fiberprocess"
ResampleVolume2 = "/tools/bin_linux64/ResampleVolume2"
ImageMath = "/tools/bin_linux64/ImageMath"
TractographyLabelMapSeeding = "/tools/Slicer4/Slicer-4.3.1-linux-amd64" \
                              "/lib/Slicer-4.3/cli-modules/TractographyLabelMapSeeding"
FiberPostProcess = "/tools/bin_linux64/FiberPostProcess"
polydatatransform = "/tools/bin_linux64/polydatatransform"
PolyDataCompression = "/tools/bin_linux64/PolyDataCompression"

DTItarget = "/NIRAL/work/jeanyves/PycharmProjects/automatic_tractography/Data/PediatricAtlas_071714FinalAtlasDTI.nrrd"
DTIsource = "/NIRAL/work/jeanyves/PycharmProjects/automatic_tractography/Data/FinalAtlasDTI.nrrd"
displacementField = "/NIRAL/work/jeanyves/PycharmProjects/automatic_tractography/displacementField.nrrd"
inputdir = "/NIRAL/work/jeanyves/PycharmProjects/automatic_tractography/Data/Fibers_Jan132015"
workdir = "/NIRAL/work/jeanyves/PycharmProjects/automatic_tractography"
dilationRadius = "2"
seedspacing = "0.5"
clthreshold = "0.15"
minimumlength = "10"
stoppingvalue = "0.12"
stoppingcurvature = "0.3"
integrationsteplength = "0.4"

step1 = 1
step2 = 1
step3 = 1
step4 = 0
step5 = 0
# 1/ co-register DTI atlases
if(step1 == 0):
    subprocess.call([DTIReg, "--movingVolume", DTItarget, "--fixedVolume", DTIsource, "--method useScalar-ANTS",
                 "--ANTSRegistrationType", "GreedyDiffeo", "--ANTSSimilarityMetric",
                 "CC","--ANTSSimilarityParameter", "4", "--outputDisplacementField", displacementField])


# 2/ mapping

if(step2 == 0):
    for file in os.listdir(inputdir):
        fiberMapped = os.path.splitext(file)[0] + "_t.vtk"
        subprocess.call([polydatatransform, "--fiber-file", inputdir + "/" + file,
                         "-o", inputdir + "/" + fiberMapped, "-D",
                         displacementField, "--inverty", "--invertx"] )

#3/ voxelize all tracts, dilate by 2 voxels and apply transform to label maps (NN) => ROIs in new atlas - OK (need ResampleVolume2?)

if(step3 == 0):
        for file in os.listdir(inputdir):
            if(file.endswith("_t.vtk")):
                labelmap = os.path.splitext(file)[0] + "_r.nrrd"
                print labelmap
                print inputdir + "/" + file
                subprocess.call([fiberprocess, "--voxelize", labelmap,
                                 "--fiber_file", inputdir + "/" + file, "-T", DTIsource])
                dilatedImage = os.path.splitext(file)[0] + "_r_dil.nrrd"
                print dilatedImage
                subprocess.call(["ImageMath", labelmap, "-dilate", str(dilationRadius) + ",1", "-outfile", dilatedImage])

#4/ Use whole tract as ROI for labelmap seeding
if(step4 == 0):
    for file in os.listdir(workdir):
        if(file.endswith("_dil.nrrd")):
            fiber = file.split("_dil.nrrd")[0] + "_r.vtp"
            subprocess.check_call([TractographyLabelMapSeeding, DTIsource, fiber, "-a", file,
                             "-s", seedspacing,
                             "--clthreshold", clthreshold,
                             "--minimumlength", minimumlength,
                             "--stoppingvalue", stoppingvalue,
                             "--stoppingcurvature", stoppingcurvature,
                             "--integrationsteplength", integrationsteplength])


#5/ post processing: cut ends with FA or WM roi
#for file in os.listdir(workdir):
#    if(file.endswith("_dil.vtp")):
#        output = file +"_tmp.vtk"
#        mask =
#subprocess.call([FiberPostProcess, "-i", file, "-o", output, "--crop", "-m", mask, "--thresholdMode", "above" ])
#FiberPostProcess -i $i -o $i:r_cleanEnds.vtk --crop -m ../ROIs/manual/FA_mask.nrrd --thresholdMode above
#subprocess.call(["ImageMath", image, "-dilate", "2,1", "-outfile", outputimage])
#subprocess.Popen(["ImageMath", image, "-dilate", "2,1", "-outfile", outputimage], stdout=subprocess.PIPE,stderr=subprocess.PIPE)

#subprocess.call([FiberPostProcess, "-i", fiber, "-o", outputfiber, "-m", mask, "--crop"])