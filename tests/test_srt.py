#!/usr/bin/env python
# coding=utf8

from __future__ import unicode_literals
from datetime import timedelta
import collections
import functools
import os
import re
import string
from io import StringIO

import pytest
from hypothesis import given, settings, HealthCheck, assume, example
import hypothesis.strategies as st

import srt

REGISTER_SETTINGS = lambda name, **kwargs: settings.register_profile(
    name, suppress_health_check=[HealthCheck.too_slow], deadline=None, **kwargs
)

REGISTER_SETTINGS("base")
REGISTER_SETTINGS("release", max_examples=1000)

settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "base"))

HOURS_IN_DAY = 24
TIMEDELTA_MAX_DAYS = 999999999
CONTENTLESS_SUB = functools.partial(
    srt.Subtitle, index=1, start=timedelta(seconds=1), end=timedelta(seconds=2)
)


def is_strictly_legal_content(content):
    return True


def subs_eq(got, expected, any_order=False):
    """
    Compare Subtitle objects using vars() so that differences are easy to
    identify.
    """
    got_vars = [frozenset(vars(sub).items()) for sub in got]
    expected_vars = [frozenset(vars(sub).items()) for sub in expected]
    if any_order:
        assert collections.Counter(got_vars) == collections.Counter(expected_vars)
    else:
        assert got_vars == expected_vars


def timedeltas(min_value=0, max_value=TIMEDELTA_MAX_DAYS):
    """
    A Hypothesis strategy to generate timedeltas.

    Right now {min,max}_value are shoved into multiple fields in timedelta(),
    which is not very customisable, but it's good enough for our current test
    purposes. If you need more precise control, you may need to add more
    parameters to this function to be able to customise more freely.
    """
    time_unit_strategy = st.integers(min_value=min_value, max_value=max_value)
    timestamp_strategy = st.builds(
        timedelta,
        hours=time_unit_strategy,
        minutes=time_unit_strategy,
        seconds=time_unit_strategy,
    )
    return timestamp_strategy


def equivalent_timestamps(min_value=0, max_value=TIMEDELTA_MAX_DAYS):
    def string_timestamp(hours, minutes, seconds, msecs, paddings):
        hours, minutes, seconds, msecs = map(
            lambda v_and_p: "0" * v_and_p[1] + str(v_and_p[0]),
            zip((hours, minutes, seconds, msecs), paddings),
        )
        return "{}:{}:{},{}".format(hours, minutes, seconds, msecs)

    def ts_field_value():
        return st.integers(min_value=min_value, max_value=max_value)

    def zero_padding():
        return st.integers(min_value=0, max_value=2)

    @st.composite
    def maybe_off_by_one_fields(draw):
        field = draw(ts_field_value())
        field_maybe_plus_one = draw(st.integers(min_value=field, max_value=field + 1))
        return field_maybe_plus_one, field

    def get_equiv_timestamps(h, m, s, ms2, ts1paddings, ts2paddings):
        h2, h1 = h
        m2, m1 = m
        s2, s1 = s
        ms1 = (
            (h2 - h1) * 60 * 60 * 1000 + (m2 - m1) * 60 * 1000 + (s2 - s1) * 1000 + ms2
        )
        return (
            string_timestamp(h2, m2, s2, ms2, ts2paddings),
            string_timestamp(h1, m1, s1, ms1, ts1paddings),
        )

    return st.builds(
        get_equiv_timestamps,
        maybe_off_by_one_fields(),
        maybe_off_by_one_fields(),
        maybe_off_by_one_fields(),
        ts_field_value(),
        st.tuples(*[zero_padding() for _ in range(4)]),
        st.tuples(*[zero_padding() for _ in range(4)]),
    )

@st.composite
def subtitles(draw, strict=True):
    """A Hypothesis strategy to generate Subtitle objects."""

    return srt.Subtitle(
        index=draw(st.integers()),
        start=draw(timedeltas()),
        end=draw(timedeltas()),
        content=draw(st.text()),
        proprietary=draw(st.text())
    )


@given(subtitles())
def test_subtitle_equality(sub_1):
    sub_2 = srt.Subtitle(**vars(sub_1))
    assert sub_1 == sub_2

@given(st.lists(subtitles()))
def test_parsing_content_with_blank_lines(subs):
    for subtitle in subs:
        # We stuff a blank line in the middle so as to trigger the "special"
        # content parsing for erroneous SRT files that have blank lines.
        subtitle.content = subtitle.content + "\n\n" + subtitle.content

    reparsed_subtitles = srt.parse(srt.compose(subs, reindex=False, strict=False))
    subs_eq(reparsed_subtitles, subs)

@given(
    st.lists(subtitles()),
    st.lists(subtitles()),
    timedeltas(min_value=-999, max_value=-1),
)
def test_subs_starts_before_zero_removed(positive_subs, negative_subs, negative_td):
    for sub in negative_subs:
        sub.start = negative_td
        sub.end = negative_td  # Just to avoid tripping any start >= end errors

    subs = positive_subs + negative_subs
    composed_subs = list(srt.sort_and_reindex(subs, in_place=True))

    # There should be no negative subs
    subs_eq(composed_subs, positive_subs, any_order=True)


@given(st.lists(subtitles(), min_size=1), st.integers(min_value=0))
def test_sort_and_reindex(input_subs, start_index):
    for sub in input_subs:
        # Pin all subs to same end time and index so that start time is
        # compared only, must be guaranteed to be < sub.start, see how
        # start_timestamp_strategy is done
        sub.end = timedelta(500001)
        sub.index = 1

    reindexed_subs = list(
        srt.sort_and_reindex(input_subs, start_index=start_index, in_place=True)
    )

    # The subtitles should be reindexed starting at start_index
    assert [sub.index for sub in reindexed_subs] == list(
        range(start_index, start_index + len(input_subs))
    )

    # The subtitles should be sorted by start time
    expected_sorting = sorted(input_subs, key=lambda sub: sub.start)
    assert reindexed_subs == expected_sorting


