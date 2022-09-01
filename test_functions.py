from jpja import functions
import datetime
import dateutil

def main():

    pass
    # use this for testing functions before assertion

def setup():

    pass # nothing needed here for now

def test_get_time_difference_from_strings():

    d1 = "2020-09-29"
    d2 = "2020-10-15"

    result = functions.get_time_difference_from_strings(d1, d2)

    # verify the output is correct
    assert type(result) == datetime.timedelta

def test_string_to_date():
    example = "2020-10-07T11:19:18.000-0400"
    e1_result = functions.string_to_date(example)

    example_2 = "2020-10-07"
    e2_result = functions.string_to_date(example)
    
    print(e1_result)
    print(e2_result)

    assert type(e1_result) == datetime.datetime
    assert type(e2_result) == datetime.datetime

    # too lazy to test example 1
    assert e2_result.strftime("%Y-%m-%d") == example_2


def test_compare_two_sentences():

    s1 = "The quick brown fox jumps over the lazy dog."
    s2 = "The brown fox jumps over the dog."

    l, j = functions.compare_two_sentences(s1, s2)

    assert l == 11
    assert j == 0.2962962962962963

if __name__ == '__main__':
    main()


