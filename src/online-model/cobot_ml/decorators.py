import numpy as np


def returns_binary(f):
    """
    Adds asserts to check if output is binary.
    """

    def wrapper(*args, **kwargs):
        output = f(*args, **kwargs)
        assert output in [
            0,
            1,
        ], f"{f.__name__} should return binary value (int or bool)"
        return output

    return wrapper


def returns_binary_array(f):
    """
    Adds asserts to check if output is a binary array.
    """

    def wrapper(*args, **kwargs):
        output = f(*args, **kwargs)
        assert np.isin(
            output, [0, 1, 0.0, 1.0]
        ).all(), f"{f.__name__} should return binary array"
        return output

    return wrapper


def returns_probability(f):
    """
    Adds asserts to check if output is a probability value.
    """

    def wrapper(*args, **kwargs):
        output = f(*args, **kwargs)
        assert 0.0 <= output <= 1.0, f"{f.__name__} should return value in 0-1 range"
        return output

    return wrapper


def returns_probability_array(f):
    """
    Adds asserts to check if output is a probability array.
    """

    def wrapper(*args, **kwargs):
        output = f(*args, **kwargs)
        assert np.logical_and(
            0 <= output, 1 >= output
        ).all(), "Probabilities should be between 0 and 1"
        return output

    return wrapper


def accepts_one_dimensional_input(input_index=0):
    def decorator(f):
        """
        Adds asserts to check if input has only one dimension.
        """

        def wrapper(*args, **kwargs):
            assert (
                args[input_index].ndim == 1
            ), f"{f.__name__} input should be one dimensional"
            return f(*args, **kwargs)

        return wrapper

    return decorator


def accepts_binary_array(input_index=0):
    def decorator(f):
        """
        Adds asserts to check if input has only one dimension.
        """

        def wrapper(*args, **kwargs):
            assert np.isin(
                args[input_index], [0.0, 1.0, 0, 1]
            ).all(), f"{f.__name__} input should be binary"
            return f(*args, **kwargs)

        return wrapper

    return decorator


def inputs_have_equal_shapes(*input_idxs):
    def decorator(f):
        """
        Adds asserts to check if inputs have the same shapes.
        """

        def wrapper(*args, **kwargs):
            shapes = [args[input_idx].shape for input_idx in input_idxs]
            assert all(
                [shape == shapes[0] for shape in shapes]
            ), f"{f.__name__} inputs should have equal shapes"
            return f(*args, **kwargs)

        return wrapper

    return decorator


def accepts_single_feature(input_index=0):
    def decorator(f):
        """
        Adds asserts to check if input contain single feature.
        """

        def wrapper(*args, **kwargs):
            assert (
                args[input_index].shape[1] == 1
            ), f"{f.__name__} input should have a single feature"
            return f(*args, **kwargs)

        return wrapper

    return decorator
