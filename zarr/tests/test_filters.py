# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division


import numpy as np
from numpy.testing import assert_array_equal, assert_array_almost_equal
from nose.tools import eq_ as eq


from numcodecs import (AsType, Delta, FixedScaleOffset, PackBits, Categorize, Zlib, Blosc, BZ2,
                       Quantize)
from zarr.creation import array
from zarr.compat import PY2


compressors = [
    None,
    Zlib(),
    BZ2(),
    Blosc(),
]

# TODO can we rely on backports and remove PY2 exclusion?
if not PY2:  # pragma: py2 no cover
    from zarr.codecs import LZMA
    compressors.append(LZMA())


def test_array_with_delta_filter():

    # setup
    astype = 'u1'
    dtype = 'i8'
    filters = [Delta(astype=astype, dtype=dtype)]
    data = np.arange(100, dtype=dtype)

    for compressor in compressors:

        a = array(data, chunks=10, compressor=compressor, filters=filters)

        # check round-trip
        assert_array_equal(data, a[:])

        # check chunks
        for i in range(10):
            cdata = a.store[str(i)]
            if compressor:
                chunk = compressor.decode(cdata)
            else:
                chunk = cdata
            actual = np.frombuffer(chunk, dtype=astype)
            expect = np.array([i * 10] + ([1] * 9), dtype=astype)
            assert_array_equal(expect, actual)


def test_array_with_astype_filter():

    # setup
    encode_dtype = 'i1'
    decode_dtype = 'i8'
    filters = [AsType(encode_dtype=encode_dtype, decode_dtype=decode_dtype)]
    chunks = 10
    chunk_size = 10
    shape = chunks * chunk_size
    data = np.arange(shape, dtype=decode_dtype)

    for compressor in compressors:

        a = array(data, chunks=chunks, compressor=compressor, filters=filters)

        # check round-trip
        assert data.dtype == a.dtype
        assert_array_equal(data, a[:])

        # check chunks
        for i in range(chunks):
            cdata = a.store[str(i)]
            if compressor:
                chunk = compressor.decode(cdata)
            else:
                chunk = cdata
            actual = np.frombuffer(chunk, dtype=encode_dtype)
            expect = data.astype(encode_dtype)[i*chunk_size:(i+1)*chunk_size]
            assert_array_equal(expect, actual)


def test_array_with_scaleoffset_filter():

    # setup
    astype = 'u1'
    dtype = 'f8'
    flt = FixedScaleOffset(scale=10, offset=1000, astype=astype, dtype=dtype)
    filters = [flt]
    data = np.linspace(1000, 1001, 34, dtype='f8')

    for compressor in compressors:

        a = array(data, chunks=5, compressor=compressor, filters=filters)

        # check round-trip
        assert_array_almost_equal(data, a[:], decimal=1)

        # check chunks
        for i in range(6):
            cdata = a.store[str(i)]
            if compressor:
                chunk = compressor.decode(cdata)
            else:
                chunk = cdata
            actual = np.frombuffer(chunk, dtype=astype)
            expect = flt.encode(data[i*5:(i*5)+5])
            assert_array_equal(expect, actual)


def test_array_with_quantize_filter():

    # setup
    dtype = 'f8'
    digits = 3
    flt = Quantize(digits=digits, dtype=dtype)
    filters = [flt]
    data = np.linspace(0, 1, 34, dtype=dtype)

    for compressor in compressors:

        a = array(data, chunks=5, compressor=compressor, filters=filters)

        # check round-trip
        assert_array_almost_equal(data, a[:], decimal=digits)

        # check chunks
        for i in range(6):
            cdata = a.store[str(i)]
            if compressor:
                chunk = compressor.decode(cdata)
            else:
                chunk = cdata
            actual = np.frombuffer(chunk, dtype=dtype)
            expect = flt.encode(data[i*5:(i*5)+5])
            assert_array_equal(expect, actual)


def test_array_with_packbits_filter():

    # setup
    flt = PackBits()
    filters = [flt]
    data = np.random.randint(0, 2, size=100, dtype=bool)

    for compressor in compressors:

        a = array(data, chunks=5, compressor=compressor, filters=filters)

        # check round-trip
        assert_array_equal(data, a[:])

        # check chunks
        for i in range(20):
            cdata = a.store[str(i)]
            if compressor:
                chunk = compressor.decode(cdata)
            else:
                chunk = cdata
            actual = np.frombuffer(chunk, dtype='u1')
            expect = flt.encode(data[i*5:(i*5)+5])
            assert_array_equal(expect, actual)


def test_array_with_categorize_filter():

    # setup
    data = np.random.choice([u'foo', u'bar', u'baz'], size=100)
    flt = Categorize(dtype=data.dtype, labels=[u'foo', u'bar', u'baz'])
    filters = [flt]

    for compressor in compressors:

        a = array(data, chunks=5, compressor=compressor, filters=filters)

        # check round-trip
        assert_array_equal(data, a[:])

        # check chunks
        for i in range(20):
            cdata = a.store[str(i)]
            if a.compressor:
                chunk = a.compressor.decode(cdata)
            else:
                chunk = cdata
            actual = np.frombuffer(chunk, dtype='u1')
            expect = flt.encode(data[i*5:(i*5)+5])
            assert_array_equal(expect, actual)


def test_compressor_as_filter():
    for compressor in compressors:
        if compressor is None:
            # skip
            continue

        # setup filters
        dtype = 'i8'
        filters = [
            Delta(dtype=dtype),
            compressor
        ]

        # setup data and arrays
        data = np.arange(10000, dtype=dtype)
        a1 = array(data, chunks=1000, compressor=None, filters=filters)
        a2 = array(data, chunks=1000, compressor=compressor,
                   filters=filters[:1])

        # check storage
        for i in range(10):
            x = bytes(a1.store[str(i)])
            y = bytes(a2.store[str(i)])
            eq(x, y)

        # check data
        assert_array_equal(data, a1[:])
        assert_array_equal(a1[:], a2[:])
