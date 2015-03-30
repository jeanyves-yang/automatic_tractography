#! /usr/bin/env python

__author__ = 'jeanyves'

import os
import sys
import logging
import signal
import subprocess
import errno

def make_sure_path_exists(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

dtiprocess = "/tools/bin_linux64/dtiprocess"
DTIReg = "/tools/bin_linux64/DTI-Reg"
fiberprocess = "/tools/bin_linux64/fiberprocess"
ResampleDTIVolume = "/tools/Slicer4/Slicer-4.3.1-linux-amd64//lib/Slicer-4.3/cli-modules/ResampleDTIVolume"
ImageMath = "/tools/bin_linux64/ImageMath"
TractographyLabelMapSeeding = "/tools/Slicer4/Slicer-4.3.1-linux-amd64" \
                              "/lib/Slicer-4.3/cli-modules/TractographyLabelMapSeeding"
FiberPostProcess = "/tools/bin_linux64/FiberPostProcess"
#FiberPostProcess = "/NIRAL/work/jeanyves/FiberPostProcess-build/bin/FiberPostProcess"
polydatatransform = "/tools/bin_linux64/polydatatransform"
PolyDataCompression = "/tools/bin_linux64/PolyDataCompression"
unu = "/tools/Slicer4/Slicer-4.3.1-linux-amd64//bin/unu"
MDT = "/NIRAL/work/jeanyves/MDT-build/bin/MaurerDistanceTransform"

DTItarget = "/NIRAL/work/jeanyves/PycharmProjects/automatic_tractography/Data/PediatricAtlas_071714FinalAtlasDTI.nrrd"
DTIsource = "/NIRAL/work/jeanyves/PycharmProjects/automatic_tractography/Data/FinalAtlasDTI.nrrd"
displacementField = "/NIRAL/work/jeanyves/PycharmProjects/automatic_tractography/displacementField.nrrd"
inputdir = "/NIRAL/work/jeanyves/PycharmProjects/automatic_tractography/Data/Fibers_Jan132015/"
workdir = "/NIRAL/work/jeanyves/PycharmProjects/automatic_tractography/"
fibersMappedDir = workdir + "fibers_mapped/"
dilationRadius = "2"
seedspacing = "1" #0.5, or inferior to 1 -> more tracts (slower to load, but mb better results)
clthreshold = "0.15"  #0
minimumlength = "10"
#maximum length 800 (default)
stoppingvalue = "0.12" #0.08
stoppingcurvature = "0.3" #0.5 (reduce it if tracts display high curv)
integrationsteplength = "0.4" #0.5

nbThresholds = "3"
nbHistogramBins = "128"
labelOffset = "0"
otsuPara = nbThresholds + "," + labelOffset + "," + nbHistogramBins

upsampledImage = workdir + "/upsampledImage.nrrd"

step1 = 1
step2 = 1
step3 = 1
step4 = 1
step5 = 0
step5a = 1
step5b = 0
step5b1 = 1
step5b2 = 1
step5b3 = 0
step5b4 = 0

# 1/ co-register DTI atlases
if(step1 == 0):
    print "Step: Co-registering atlases & creation of the displacement field ..."
    subprocess.call([DTIReg, "--movingVolume", DTItarget, "--fixedVolume", DTIsource, "--method useScalar-ANTS",
                 "--ANTSRegistrationType", "GreedyDiffeo", "--ANTSSimilarityMetric",
                 "CC","--ANTSSimilarityParameter", "4", "--outputDisplacementField", displacementField])
    print "Step: Co-registration DONE"

# 2/ mapping

if(step2 == 0):
    print "Step: Mapping reference tracts ..."
    make_sure_path_exists(workdir + "fibers_mapped")
    for file in os.listdir(inputdir):
        fiberMapped = fibersMappedDir + os.path.splitext(file)[0] + "_t.vtk"
        subprocess.call([polydatatransform, "--fiber_file", inputdir + file,
                         "-o", fiberMapped, "-D",
                         displacementField, "--inverty", "--invertx"] )
    print "Step: Mapping DONE"

#3/ voxelize all tracts, dilate by 2 voxels and apply transform to label maps (NN) => R../../processing.cxxOIs in new atlas - OK (need ResampleVolume2?)

if(step3 == 0):
    print "Step: Dilation & voxelization of mapped reference tracts ..."
    make_sure_path_exists(workdir + "dilated_images")
    for file in os.listdir(fibersMappedDir):
        if(file.endswith("_t.vtk")):
            print file
            labelmap = os.path.splitext(file)[0] + ".nrrd"
            subprocess.call([fiberprocess, "--voxelize", workdir + "dilated_images/" + labelmap,
                             "--fiber_file", fibersMappedDir + file, "-T", DTIsource])
            dilatedImage = os.path.splitext(file)[0] + "_dil.nrrd"
            subprocess.call([ImageMath,  workdir + "dilated_images/" + labelmap, "-dilate", str(dilationRadius) + ",1", "-outfile",
                             workdir + "dilated_images/" + dilatedImage])
    print "Step: Dilation & voxelization DONE"


#4/ Use whole tract as ROI for labelmap seeding

if(step4 == 0):
    print "Step: TractographyLabelMapSeeding ... "
    for file in os.listdir(workdir + "dilated_images"):
        if(file.endswith("_dil.nrrd")):
            print file
            make_sure_path_exists(workdir + "fibers_processed")
            fiber = workdir + "fibers_processed/" + file[:-9] + "_1ss.vtp"
            subprocess.check_call([TractographyLabelMapSeeding, DTIsource, fiber, "-a", workdir + "dilated_images/" + file,
                             "-s", seedspacing,
                             "--clthreshold", clthreshold,
                             "--minimumlength", minimumlength,
                             "--stoppingvalue", stoppingvalue,
                             "--stoppingcurvature", stoppingcurvature,
                             "--integrationsteplength", integrationsteplength])
    print "Step: Tractography using label map seeding DONE"


#5/ post processing: cut ends with FA or WM roi

if(step5 == 0):
    print "Step: Processing tracts ..."
    FAImage = workdir + "FinalAtlasDTI_FA.nrrd"
    MDImage = workdir + "FinalAtlasDTI_MD.nrrd"
    WMmask = workdir + "WMmask.nrrd"
    MDmask = workdir + "MDmask.nrrd"
# a/ create WM mask and MD mask
    if( step5a == 0 ):
        print "Creation of WM mask ..."
        #for now need to create MD mask or provide it (could create it automatically with the atlas provided + dtiprocess)
        subprocess.call([ImageMath, FAImage, "-outfile", WMmask, "-dilate", "10,10"])
        subprocess.call([ImageMath, WMmask, "-otsu", "-outfile", WMmask])
        print "DONE"
        print "creation of CSF mask ..."
        subprocess.call([dtiprocess, "--dti_image", DTIsource, "-m", MDImage])
        subprocess.call([ImageMath, MDImage, "-outfile", MDmask, "-otsuMultipleThresholds", "-otsuPara", otsuPara])
        subprocess.call([ImageMath, MDmask, "-outfile", MDmask, "-erode", "2,1"])
        print "DONE"
# b/ process
    if( step5b == 0 ):
        if(step5b1 == 0):
            print "creation of upsampled image ..."
            subprocess.call([unu, "resample", "-i", FAImage, "-o", upsampledImage, "-s", "x2", "x2", "x2" ])
            subprocess.call([ResampleDTIVolume, DTIsource, upsampledImage, "-R", upsampledImage ])
            print "DONE"
        if(step5b2 ==0):
            print "Step: Cropping reference tracts ..."
            for file in os.listdir(fibersMappedDir):
                if(file.endswith("_t.vtk")):
                    print file
                    fiberCropped = fibersMappedDir + os.path.splitext(file)[0] + "_cleanEnds.vtk"
                    subprocess.call([FiberPostProcess, "-i", fibersMappedDir + file,
                                    "-o", fiberCropped, "--crop", "-m", WMmask,
                                             "--thresholdMode", "above"])
            print "Step: Cropping reference tracts DONE"

        for file in os.listdir(workdir + "fibers_processed/" ):
            if(file.endswith("_t_1ss.vtp")):
                print file
                dilatedImage = workdir + "dilated_images/" + os.path.splitext(file)[0] + "_dil.nrrd"
                outputCrop = workdir + "fibers_processed/" + os.path.splitext(file)[0] + "_cleanEnds.vtp"
                outputMaskCSF = workdir + "fibers_processed/" + os.path.splitext(file)[0] + "_maskCSF.vtp"
                outputMaskTract = workdir + "fibers_processed/" + os.path.splitext(file)[0] + "_maskTract.vtp"
                outputLengthMatch = workdir + "fibers_processed/" + os.path.splitext(file)[0] + "_lengthMatch.vtp"
                outputFiber5 = workdir + "fibers_processed/" + os.path.splitext(file)[0] + "_threshold5.vtp"
                outputFiber3 = workdir + "fibers_processed/" + os.path.splitext(file)[0] + "_threshold3.vtp"
                outputFiber2 = workdir + "fibers_processed/" + os.path.splitext(file)[0] + "_threshold2.vtp"
                lengthMatchFiber = fibersMappedDir + os.path.splitext(file)[0] + "_cleanEnds.vtk"
                if(step5b3 == 0):
                    print "cropping using WM mask..."
                    subprocess.call([FiberPostProcess, "-i", workdir + "fibers_processed/" + file, "-o", outputCrop, "--crop", "-m", WMmask,
                                     "--thresholdMode", "above"])
                    print "DONE"
                    print "masking with CSF mask ..."
                    subprocess.call([FiberPostProcess, "-i", outputCrop, "-o", outputMaskCSF, "--mask", "--clean", "-m", MDmask,
                              "--thresholdMode", "above", "-t", "0.001"])
                    print "DONE"
                    print "masking with dilated reference image ..."
                    subprocess.call([FiberPostProcess, "-i", outputMaskCSF, "-o", outputMaskTract, "--mask", "-m",
                                     dilatedImage, "--thresholdMode", "below", "-t", "0.6", "--clean"
                                     ])
                    print "DONE"
                    print "matching length with reference tract ..."
                    subprocess.call([FiberPostProcess, "-i", outputMaskTract, "--lengthMatch", lengthMatchFiber,
                                     "-o", outputLengthMatch])
                    print "DONE"
                if(step5b4 == 0):
                    make_sure_path_exists(workdir + "ref_fibers_voxelized")
                    voxelizedImage = workdir + "ref_fibers_voxelized/"  + file[:-4] + "_voxelized.nrrd"
                    print "voxelization of the tract ..."
                    subprocess.call([fiberprocess, "--voxelize", voxelizedImage, "--fiber_file", lengthMatchFiber, "-T", upsampledImage])
                    distanceMap = inputdir + "/" + file[:-8] + "_distanceMap.nrrd"
                    print "DONE"
                    print "creation of the distance map of the reference tract ..."
                    subprocess.call([MDT, voxelizedImage, distanceMap ])
                    print "DONE"
                    print "matching tract with the distance map ..."
                    subprocess.call([FiberPostProcess, "-i", outputLengthMatch, "-o", outputFiber5, "-m",
                                    distanceMap, "--threshold", "5", "--mask", "--clean", "--thresholdMode", "above" ])
                    subprocess.call([FiberPostProcess, "-i", outputLengthMatch, "-o", outputFiber3, "-m",
                                    distanceMap, "--threshold", "3", "--mask", "--clean", "--thresholdMode", "above" ])
                    subprocess.call([FiberPostProcess, "-i", outputLengthMatch, "-o", outputFiber2, "-m",
                                    distanceMap, "--threshold", "2", "--mask", "--clean", "--thresholdMode", "above" ])
                    print "DONE"
    print "Step: Processing tracts DONE"
