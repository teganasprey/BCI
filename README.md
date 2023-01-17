# __BCI Research__

This repo contains all materials necessary to analyze a set of data collected as part of a study on motor imagery BCI. The data can be downloaded from: [BCI Data](https://figshare.com/collections/A_large_electroencephalographic_motor_imagery_dataset_for_electroencephalographic_brain_computer_interfaces/3917698),

The repo is organized as follows:

## Data
This directory contains an explanation of the data format. The data files were too large to include directly in the repo.

## Preprocessing
Preprocessing of the EEG data is an important step toward the efficient extraction of salient features. Several preprocessing methods are included in the repo, and include the following:

### CSP
Common Spatial Pattern (CSP) is a procedure used in signal multichannel EEG preprocessing to discriminate EEGs based on the covariance between the potential variations at the electrode sites. It is an effective method for feature extraction between two classes.

### PCA
Principal component analysis (PCA) is a mathematical algorithm that reduces the dimensionality of the data while retaining most of its variation. It identifies directions, called principal components, along which the variation in the data is maximal.

### ICA
Independent component analysis (ICA) is a blind source separation technique.  Source signals are often corrupted by noise or other independent signals. Blind source separation (BSS) can separate signals from a combination of independent sources, even if little information is known about the source signals. 

### FFT
The discrete Fourier transform (DFT) is a mathematical tool to describe the relationship between the time domain and frequency domain representation of discrete signals. Various DFT computation techniques are known collectively as the fast Fourier transform (FFT). 

### DWT
The Discrete Wavelet Transform (DWT) decomposes a signal into a set of mutually orthogonal wavelet basis functions. DWT refers to a set of transforms, each with a different set of wavelet basis functions.

### Digital Filtering
Digital filters play an important role in EEG analysis. Digital filters work by suppressing artifacts, or unwanted noise, in EEG data. The primary types of filters include low-pass, high-pass, bandpass, and notch filters. 

## Models
Several modelling techniques are included in the repo. These include methods for classification of feature and signals, including the following:

### ELM

### KNN

### LDA

### Naive Bayes

### SVM

In addition to classification algorithms, the repo also includes several implementations of neural network models, including the following:

### CNN

### DNN

### LSTM
 

## Papers
When possible, we include the supporting academic papers or books for the methods and algorithms contained in the repo.
