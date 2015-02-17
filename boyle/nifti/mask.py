# coding=utf-8
"""
Utilities to compute/apply masking from Nifti images
"""
# ------------------------------------------------------------------------------
# Author: Alexandre Manhaes Savio <alexsavio@gmail.com>
# Wrocław University of Technology
#
# 2015, Alexandre Manhaes Savio
# Use this at your own risk!
# ------------------------------------------------------------------------------

import logging
import numpy   as np
import nibabel as nib

from .read              import get_img_data
from ..exceptions       import NiftiFilesNotCompatible
from ..utils.numpy_mem  import as_ndarray
from .check             import (are_compatible_imgs, check_img, repr_imgs,
                                check_img_compatibility, get_data)

log = logging.getLogger(__name__)


def load_mask(image, allow_empty=True):
    """Load a Nifti mask volume.

    Parameters
    ----------
    image: img-like object or boyle.nifti.NeuroImage or str
        Can either be:
        - a file path to a Nifti image
        - any object with get_data() and get_affine() methods, e.g., nibabel.Nifti1Image.
        If niimg is a string, consider it as a path to Nifti image and
        call nibabel.load on it. If it is an object, check if get_data()
        and get_affine() methods are present, raise TypeError otherwise.

    allow_empty: boolean, optional
        Allow loading an empty mask (full of 0 values)

    Returns
    -------
    nibabel.Nifti1Image with boolean data.
    """
    try:
        img    = check_img(image, make_it_3d=True)
        values = np.unique(img.get_data())
    except:
        log.exception('Error reading mask {}.'.format(repr_imgs(image)))
        raise

    if len(values) == 1:
        # We accept a single value if it is not 0 (full true mask).
        if values[0] == 0 and not allow_empty:
            raise ValueError('Given mask is invalid because it masks all data')

    elif len(values) == 2:
        # If there are 2 different values, one of them must be 0 (background)
        if 0 not in values:
            raise ValueError('Background of the mask must be represented with 0.'
                             ' Given mask contains: {}.'.format(values))

    elif len(values) != 2:
        # If there are more than 2 values, the mask is invalid
            raise ValueError('Given mask is not made of 2 values: {}. '
                             'Cannot interpret as true or false'.format(values))

    return nib.Nifti1Image(as_ndarray(get_img_data(img), dtype=bool), img.get_affine(), img.get_header())


def load_mask_data(image, allow_empty=True):
    """Load a Nifti mask volume and return its data matrix as boolean and affine.

    Parameters
    ----------
    image: img-like object or boyle.nifti.NeuroImage or str
        Can either be:
        - a file path to a Nifti image
        - any object with get_data() and get_affine() methods, e.g., nibabel.Nifti1Image.
        If niimg is a string, consider it as a path to Nifti image and
        call nibabel.load on it. If it is an object, check if get_data()
        and get_affine() methods are present, raise TypeError otherwise.

    allow_empty: boolean, optional
        Allow loading an empty mask (full of 0 values)

    Returns
    -------
    numpy.ndarray with dtype==bool, numpy.ndarray of affine transformation
    """
    try:
        mask = load_mask(image, allow_empty=allow_empty)
    except:
        log.exception('Error loading mask {}.'.format(repr_imgs(image)))
        raise
    else:
        return get_img_data(mask), mask.get_affine()


def binarise(image, threshold=0):
    """Binarise image with the given threshold

    Parameters
    ----------
    image: img-like object or boyle.nifti.NeuroImage or str
        Can either be:
        - a file path to a Nifti image
        - any object with get_data() and get_affine() methods, e.g., nibabel.Nifti1Image.
        If niimg is a string, consider it as a path to Nifti image and
        call nibabel.load on it. If it is an object, check if get_data()
        and get_affine() methods are present, raise TypeError otherwise.

    threshold: float

    Returns
    -------
    binarised img-like object
    """
    try:
        img = check_img(image)
        vol = img.get_data() > threshold
    except Exception:
        log.exception('Error creating mask from file {0}.'.format(repr_imgs(image)))
        raise
    else:
        return vol


def union_mask(filelist):
    """
    Creates a binarised mask with the union of the files in filelist.

    Parameters
    ----------
    filelist: list of img-like object or boyle.nifti.NeuroImage or str
        List of paths to the volume files containing the ROIs.
        Can either be:
        - a file path to a Nifti image
        - any object with get_data() and get_affine() methods, e.g., nibabel.Nifti1Image.
        If niimg is a string, consider it as a path to Nifti image and
        call nibabel.load on it. If it is an object, check if get_data()
        and get_affine() methods are present, raise TypeError otherwise.

    Returns
    -------
    ndarray of bools
        Mask volume

    Raises
    ------
    ValueError
    """
    firstimg = check_img(filelist[0])
    mask     = np.zeros_like(firstimg.get_data())

    # create space for all features and read from subjects
    try:
        for volf in filelist:
            roiimg = check_img(volf)
            check_img_compatibility(firstimg, roiimg)
            mask  += get_img_data(roiimg)
    except Exception:
        msg = 'Error joining mask {} and {}.'.format(repr_imgs(firstimg), repr_imgs(roiimg))
        log.exception(msg)
        raise ValueError(msg)
    else:
        return as_ndarray(mask > 0, dtype=bool)


def apply_mask(image, mask_img):
    """Read a Nifti file nii_file and a mask Nifti file.
    Returns the voxels in nii_file that are within the mask, the mask indices
    and the mask shape.

    Parameters
    ----------
    image: img-like object or boyle.nifti.NeuroImage or str
        Can either be:
        - a file path to a Nifti image
        - any object with get_data() and get_affine() methods, e.g., nibabel.Nifti1Image.
        If niimg is a string, consider it as a path to Nifti image and
        call nibabel.load on it. If it is an object, check if get_data()
        and get_affine() methods are present, raise TypeError otherwise.

    mask_img: img-like object or boyle.nifti.NeuroImage or str
        3D mask array: True where a voxel should be used.
        See img description.

    Returns
    -------
    vol[mask_indices], mask_indices

    Note
    ----
    nii_file and mask_file must have the same shape.

    Raises
    ------
    NiftiFilesNotCompatible, ValueError
    """
    try:
        img  = check_img(image)
        mask = check_img(mask_img)
        check_img_compatibility(img, mask)
    except:
        msg = 'Images {} and {} are not compatible.'.format(repr_imgs(image), repr_imgs(mask_img))
        log.exception(msg)
        raise NiftiFilesNotCompatible(repr_imgs(image), repr_imgs(mask_img))

    try:
        vol       = img.get_data()
        mask      = load_mask(mask_img)
        mask_data = get_data (mask)
        indices   = np.where (mask_data)
    except:
        msg = 'Error applying mask {} to {}.'.format(repr_imgs(mask_img), repr_imgs(img))
        log.exception(msg)
        raise ValueError(msg)
    else:
        return vol[mask_data], indices


def apply_mask_4d(image, mask_img): # , smooth_mm=None, remove_nans=True):
    """Read a Nifti file nii_file and a mask Nifti file.
    Extract the signals in nii_file that are within the mask, the mask indices
    and the mask shape.

    Parameters
    ----------
    image: img-like object or boyle.nifti.NeuroImage or str
        Can either be:
        - a file path to a Nifti image
        - any object with get_data() and get_affine() methods, e.g., nibabel.Nifti1Image.
        If niimg is a string, consider it as a path to Nifti image and
        call nibabel.load on it. If it is an object, check if get_data()
        and get_affine() methods are present, raise TypeError otherwise.

    mask_img: img-like object or boyle.nifti.NeuroImage or str
        3D mask array: True where a voxel should be used.
        See img description.

    smooth_mm: float #TBD
        (optional) The size in mm of the FWHM Gaussian kernel to smooth the signal.
        If True, remove_nans is True.

    remove_nans: bool #TBD
        If remove_nans is True (default), the non-finite values (NaNs and
        infs) found in the images will be replaced by zeros.

    Returns
    -------
    vol[mask_indices], mask_indices

    session_series: numpy.ndarray
        2D array of series with shape (image number, voxel number)

    mask_indices: numpy.ndarray

    Note
    ----
    nii_file and mask_file must have the same shape.

    Raises
    ------
    FileNotFound, NiftiFilesNotCompatible
    """
    try:
        img  = check_img(image)
        mask = check_img(mask_img)
        check_img_compatibility(img, mask, only_check_3d=True)
    except:
        msg = 'Images {} and {} are not compatible.'.format(repr_imgs(image), repr_imgs(mask_img))
        log.exception(msg)
        raise NiftiFilesNotCompatible(repr_imgs(image), repr_imgs(mask_img))

    try:
        vol = get_data(img)
        data, indices = _apply_mask_to_4d_data(vol, mask)
    except:
        msg = 'Error applying mask {} to {}.'.format(repr_imgs(image), repr_imgs(mask_img))
        log.exception(msg)
        raise ValueError(msg)
    else:
        return data, indices, vol.shape


def _apply_mask_to_4d_data(vol_data, mask_img):
    """
    Parameters
    ----------
    vol_data:
    mask_img:

    Returns
    -------
    vol[mask_indices], mask_indices, mask.shape

    : numpy.ndarray
        2D array of series with shape (image number, voxel number)

    mask_indices:

    Note
    ----
    vol_data and mask_file must have the same shape.
    """
    try:
        mask_data, _ = load_mask_data(mask_img)
        data         = vol_data[mask_data]
    except:
        raise
    else:
        return data, np.where(mask_data)


def niftilist_mask_to_array(img_filelist, mask_file=None, outdtype=None):
    """From the list of absolute paths to nifti files, creates a Numpy array
    with the masked data.

    Parameters
    ----------
    img_filelist: list of str
        List of absolute file paths to nifti files. All nifti files must have
        the same shape.

    mask_file: str
        Path to a Nifti mask file.
        Should be the same shape as the files in nii_filelist.

    outdtype: dtype
        Type of the elements of the array, if not set will obtain the dtype from
        the first nifti file.

    Returns
    -------
    outmat:
        Numpy array with shape N x prod(vol.shape) containing the N files as flat vectors.

    mask_indices:
        Tuple with the 3D spatial indices of the masking voxels, for reshaping
        with vol_shape and remapping.

    vol_shape:
        Tuple with shape of the volumes, for reshaping.

    """
    img = check_img(img_filelist[0])
    if not outdtype:
        outdtype = img.dtype

    mask      = load_mask   (mask_file)
    mask_data = get_img_data(mask)
    indices   = np.where    (mask_data)

    outmat = np.zeros((len(img_filelist), np.count_nonzero(mask)),
                      dtype=outdtype)

    try:
        for i, img_item in enumerate(img_filelist):
            img = check_img(img_item)
            if not are_compatible_imgs(img, mask_file):
                raise NiftiFilesNotCompatible(repr_imgs(img), repr_imgs(mask_file))

            vol = get_img_data(img)
            outmat[i, :] = vol[indices]
    except Exception:
        log.exception('Error when reading file {0}.'.format(repr_imgs(img)))
        raise
    else:
        return outmat, indices, mask_data.shape
