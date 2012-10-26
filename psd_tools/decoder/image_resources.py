# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import io
import warnings
import collections

from psd_tools.utils import read_pascal_string, unpack, read_fmt, read_unicode_string, be_array_from_bytes
from psd_tools.constants import ImageResourceID, PrintScaleStyle
from psd_tools.decoder import decoders

_image_resource_decoders, register = decoders.new_registry()

_image_resource_decoders.update({
    ImageResourceID.LAYER_STATE_INFO:           decoders.single_value("H"),
    ImageResourceID.WATERMARK:                  decoders.single_value("B"),
    ImageResourceID.ICC_UNTAGGED_PROFILE:       decoders.boolean(),
    ImageResourceID.EFFECTS_VISIBLE:            decoders.boolean(),
    ImageResourceID.IDS_SEED_NUMBER:            decoders.single_value("I"),
    ImageResourceID.INDEXED_COLOR_TABLE_COUNT:  decoders.single_value("H"),
    ImageResourceID.TRANSPARENCY_INDEX:         decoders.single_value("H"),
    ImageResourceID.GLOBAL_ALTITUDE:            decoders.single_value("I"),
    ImageResourceID.GLOBAL_ANGLE_OBSOLETE:      decoders.single_value("I"),
    ImageResourceID.COPYRIGHT_FLAG:             decoders.boolean("H"),

    ImageResourceID.ALPHA_NAMES_UNICODE:        decoders.unicode_string,
    ImageResourceID.WORKFLOW_URL:               decoders.unicode_string,
})

PrintScale = collections.namedtuple('PrintScale', 'style, x, y, scale')
PrintFlags = collections.namedtuple('PrintFlags', 'labels, crop_marks, color_bars, registration_marks, negative, flip, interpolate, caption, print_flags')
PrintFlagsInfo = collections.namedtuple('PrintFlagsInfo', 'version, center_crop_marks, bleed_width_value, bleed_width_scale')
VersionInfo = collections.namedtuple('VersionInfo', 'version, has_real_merged_data, writer_name, reader_name, file_version')
PixelAspectRation = collections.namedtuple('PixelAspectRatio', 'version aspect')

def decode(image_resource_blocks):
    """
    Replaces ``data`` of image resource blocks with parsed data structures.
    """
    return [parse_image_resource(res) for res in image_resource_blocks]

def parse_image_resource(resource):
    """
    Replaces ``data`` of image resource block with a parsed data structure.
    """
    if not ImageResourceID.is_known(resource.resource_id):
        warnings.warn("Unknown resource_id (%s)" % resource.resource_id)

    decoder = _image_resource_decoders.get(resource.resource_id, lambda data: data)
    return resource._replace(data = decoder(resource.data))

@register(ImageResourceID.LAYER_GROUP_INFO)
def _decode_layer_group_info(data):
    return be_array_from_bytes("H", data)

@register(ImageResourceID.LAYER_SELECTION_IDS)
def _decode_layer_selection(data):
    return be_array_from_bytes("I", data[2:])

@register(ImageResourceID.LAYER_GROUPS_ENABLED_ID)
def _decode_layer_groups_enabled_id(data):
    return be_array_from_bytes("B", data)


@register(ImageResourceID.VERSION_INFO)
def _decode_version_info(data):
    fp = io.BytesIO(data)

    return VersionInfo(
        read_fmt("I", fp)[0],
        read_fmt("?", fp)[0],
        read_unicode_string(fp),
        read_unicode_string(fp),
        read_fmt("I", fp)[0],
    )

@register(ImageResourceID.PIXEL_ASPECT_RATIO)
def _decode_pixel_aspect_ration(data):
    version = unpack("I", data[:4])[0]
    aspect = unpack("d", data[4:])[0]
    return PixelAspectRation(version, aspect)

@register(ImageResourceID.PRINT_FLAGS)
def _decode_print_flags(data):
    # FIXME: the following assertion fails so there is
    # something wrong with this function:
    #
    # assert len(data) == 9, (data, len(data))
    return PrintFlags(*(unpack("9?", data[:9])))

@register(ImageResourceID.PRINT_FLAGS_INFO)
def _decode_print_flags_info(data):
    return PrintFlagsInfo(*(unpack("HBxIh", data)))

@register(ImageResourceID.PRINT_SCALE)
def _decode_print_scale(data):
    style, x, y, scale = unpack("H3f", data)

    if not PrintScaleStyle.is_known(style):
        warnings.warn("Unknown print scale style (%s)" % style)

    return PrintScale(style, x, y, scale)


@register(ImageResourceID.CAPTION_PASCAL)
def _decode_caption_pascal(data):
    fp = io.BytesIO(data)
    return read_pascal_string(fp, 'ascii')
