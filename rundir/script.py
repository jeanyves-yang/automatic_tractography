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
#FiberPostProcess = "/tools/bin_linux64/FiberPostProcess"
FiberPostProcess = "/NIRAL/work/jeanyves/FiberPostProcess-build/bin/FiberPostProcess"
polydatatransform = "/tools/bin_linux64/polydatatransform"
PolyDataCompression = "/tools/bin_linux64/PolyDataCompression"
unu = "/tools/Slicer4/Slicer-4.3.1-linux-amd64//bin/unu"

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

nbThresholds = "3"
nbHistogramBins = "128"
labelOffset = "0"
otsuPara = nbThresholds + "," + labelOffset + "," + nbHistogramBins

step1 = 1
step2 = 1
step3 = 1
step4 = 1
step5 = 0
step5a = 0
step5b = 0
# 1/ co-register DTI atlases
if(step1 == 0):
    subprocess.call([DTIReg, "--movingVolume", DTItarget, "--fixedVolume", DTIsource, "--method useScalar-ANTS",
                 "--ANTSRegistrationType", "GreedyDiffeo", "--ANTSSimilarityMetric",
                 "CC","--ANTSSimilarityParameter", "4", "--outputDisplacementField", displacementField])


# 2/ mapping

if(step2 == 0):
    for file in os.listdir(inputdir):
        if( file == "Arc_R_FrontoParietal_bundle_clean.vtk"):
            fiberMapped = os.path.splitext(file)[0] + "_t.vtk"
            subprocess.call([polydatatransform, "--fiber-file", inputdir + "/" + file,
                             "-o", inputdir + "/" + fiberMapped, "-D",
                             displacementField, "--inverty", "--invertx"] )

#3/ voxelize all tracts, dilate by 2 voxels and apply transform to label maps (NN) => ROIs in new atlas - OK (need ResampleVolume2?)

if(step3 == 0):
        for file in os.listdir(inputdir):
            if(file.endswith("_t.vtk")):
                    labelmap = os.path.splitext(file)[0] + ".nrrd"
                    subprocess.call([fiberprocess, "--voxelize", labelmap,
                                     "--fiber_file", inputdir + "/" + file, "-T", DTIsource])
                    dilatedImage = os.path.splitext(file)[0] + "_dil.nrrd"
                    subprocess.call([ImageMath, labelmap, "-dilate", str(dilationRadius) + ",1", "-outfile", dilatedImage])

#4/ Use whole tract as ROI for labelmap seeding

if(step4 == 0):
    for file in os.listdir(workdir):
        if(file.endswith("_dil.nrrd")):
            #fiber = file.split("_dil.nrrd")[0] + "_dil.vtp"
            fiber = os.path.splitext(file)[0] + ".vtp"
            subprocess.check_call([TractographyLabelMapSeeding, DTIsource, fiber, "-a", file,
                             "-s", seedspacing,
                             "--clthreshold", clthreshold,
                             "--minimumlength", minimumlength,
                             "--stoppingvalue", stoppingvalue,
                             "--stoppingcurvature", stoppingcurvature,
                             "--integrationsteplength", integrationsteplength])


#5/ post processing: cut ends with FA or WM roi

if(step5 == 0):

# a/ create WM mask and MD mask
    if( step5a == 0 ):
        FAImage = workdir + "/FinalAtlasDTI_FA.nrrd"
        #for now need to create MD mask or provide it (could create it automatically with the atlas provided + dtiprocess)
        MDImage = workdir + "/FinalAtlasDTI_MD.nrrd"
        WMmask = workdir + "/WMmask.nrrd"
        MDmask = workdir + "/MDmask.nrrd"
        subprocess.call([ImageMath, FAImage, "-outfile", WMmask, "-dilate", "10,10"])
        subprocess.call([ImageMath, WMmask, "-otsu", "-outfile", WMmask])
        subprocess.call([ImageMath, MDImage, "-outfile", MDmask, "-otsuMultipleThresholds", "-otsuPara", otsuPara]
                    )

# b/ process
    if( step5b == 0 ):
        subprocess.call([ImageMath, MDmask, "-outfile", MDmask, "-erode", "2,1"])
        for file in os.listdir(inputdir):
            if(file.endswith("_clean_t.vtk")):
                outputCrop = inputdir + "/" + os.path.splitext(file)[0] + "_o_cleanEnds.vtk"
                subprocess.call([FiberPostProcess, "-i", inputdir + "/" + file, "-o", outputCrop, "--crop", "-m", WMmask,
                                 "--thresholdMode", "above" ])
                print outputCrop

        for file in os.listdir(workdir):
            if(file.endswith("_dil.vtp")):
                print file
                dilatedImage = workdir + "/" + os.path.splitext(file)[0] + ".nrrd"
                outputCrop = os.path.splitext(file)[0] + "_cleanEnds.vtp"
                outputMaskCSF = os.path.splitext(file)[0] + "_maskCSF.vtp"
                outputMaskTract = os.path.splitext(file)[0] + "_maskTract.vtp"
                outputFiber = workdir + "/" + "outputFiber.vtk"
                lengthMatchFiber = inputdir + "/" + file[:-8] + "_o_cleanEnds.vtk"
                subprocess.call([FiberPostProcess, "-i", file, "-o", outputCrop, "--crop", "-m", WMmask,
                                 "--thresholdMode", "above"])
                subprocess.call([FiberPostProcess, "-i", outputCrop, "-o", outputMaskCSF, "--mask", "--clean", "-m", MDmask,
                          "--thresholdMode", "above", "-t", "0.001"])
                subprocess.call([FiberPostProcess, "-i", outputMaskCSF, "-o", outputMaskTract, "--mask", "-m",
                                 dilatedImage, "--thresholdMode", "below", "-t", "0.7", "--clean"
                                 ])
                subprocess.call([FiberPostProcess, "-i", outputMaskTract, "--lengthMatch", lengthMatchFiber,
                                 "-o", outputFiber])
                print "DONE"
