import numpy as np
from scipy.stats import mode


def find_grid(image):
    # Looks for the grid in image and returns color and size
    grid_color = -1
    size = [0, 0]
    # TODO: border = False

    for color in range(10):
        for i in range(size[0] + 1, image.shape[0] // 2 + 1):
            if (image.shape[0] + 1) % i == 0:
                step = (image.shape[0] + 1) // i
                if (image[(step - 1) :: step] == color).all():
                    size[0] = i
                    grid_color = color
        for i in range(size[1] + 1, image.shape[1] // 2 + 1):
            if (image.shape[1] + 1) % i == 0:
                step = (image.shape[1] + 1) // i
                if (image[:, (step - 1) :: step] == color).all():
                    size[1] = i
                    grid_color = color

    return grid_color, size


def find_color_boundaries(array, color):
    # Looks for the boundaries of any color and returns them
    if (array == color).any() == False:
        return None
    ind_0 = np.arange(array.shape[0])
    ind_1 = np.arange(array.shape[1])

    temp_0 = ind_0[(array == color).max(axis=1)]  # axis 0
    min_0, max_0 = temp_0.min(), temp_0.max()

    temp_1 = ind_1[(array == color).max(axis=0)]  # axis 1
    min_1, max_1 = temp_1.min(), temp_1.max()

    return min_0, max_0, min_1, max_1


def get_color_max(image, color):
    # Returns the part of the image inside the color boundaries
    boundaries = find_color_boundaries(image, color)
    if boundaries:
        return (
            0,
            image[boundaries[0] : boundaries[1] + 1, boundaries[2] : boundaries[3] + 1],
        )
    else:
        return 1, None


def get_voting_corners(image, operation="rotate"):
    # Producing new image with 1/4 of initial size
    # by stacking of 4 rotated or reflected coners
    # and choosing the most popular color for each pixel
    # (restores symmetrical images with noise)"
    if operation not in ["rotate", "reflect"]:
        return 1, None
    if operation == "rotate":
        if image.shape[0] != image.shape[1]:
            return 2, None
        size = (image.shape[0] + 1) // 2
        voters = np.stack(
            [
                image[:size, :size],
                np.rot90(image[:size, -size:], k=1),
                np.rot90(image[-size:, -size:], k=2),
                np.rot90(image[-size:, :size], k=3),
            ]
        )

    if operation == "reflect":
        sizes = ((image.shape[0] + 1) // 2, (image.shape[1] + 1) // 2)
        voters = np.stack(
            [
                image[: sizes[0], : sizes[1]],
                image[: sizes[0], -sizes[1] :][:, ::-1],
                image[-sizes[0] :, -sizes[1] :][::-1, ::-1],
                image[-sizes[0] :, : sizes[1]][::-1, :],
            ]
        )
    return 0, mode(voters, axis=0).mode[0]


def get_grid(image, grid_size, cell):
    """ returns the particular cell form the image with grid"""
    if cell[0] >= grid_size[0] or cell[1] >= grid_size[1]:
        return 1, None
    steps = ((image.shape[0] + 1) // grid_size[0], (image.shape[1] + 1) // grid_size[1])
    block = image[
        steps[0] * cell[0] : steps[0] * (cell[0] + 1) - 1,
        steps[1] * cell[1] : steps[1] * (cell[1] + 1) - 1,
    ]
    return 0, block


def get_half(image, side):
    """ returns the half of the image"""
    if side not in "lrtb":
        return 1, None
    if side == "l":
        return 0, image[:, : (image.shape[1] + 1) // 2]
    if side == "r":
        return 0, image[:, -(image.shape[1] + 1) // 2 :]
    if side == "t":
        return 0, image[-(image.shape[0] + 1) // 2 :, :]
    if side == "b":
        return 0, image[: (image.shape[0] + 1) // 2, :]


def get_rotation(image, k):
    return 0, np.rot90(image, k)


def get_transpose(image):
    return 0, np.transpose(image)


def get_roll(image, shift, axis):
    return 0, np.roll(image, shift=shift, axis=axis)


def get_cut_edge(image, l, r, t, b):
    """deletes pixels from some sided of an image"""
    return 0, image[t : image.shape[0] - b, l : image.shape[1] - r]


def get_resize(image, scale):
    """ resizes image according to scale"""
    if image.shape[0] % scale != 0 or image.shape[1] % scale != 0:
        return 1, None
    if image.shape[0] <= scale or image.shape[1] <= scale:
        return 2, None

    arrays = []
    size = image.shape[0] // scale, image.shape[1] // scale
    for i in range(size[0]):
        for j in range(size[1]):
            arrays.append(image[i :: size[0], j :: size[1]])

    result = mode(np.stack(arrays), axis=0).mode[0]

    return 0, result


def get_reflect(image, side):
    """ returns images generated by reflections of the input"""
    if side not in ["r", "l", "t", "b", "rt", "rb", "lt", "lb"]:
        return 1, None
    try:
        if side == "r":
            result = np.zeros((image.shape[0], image.shape[1] * 2 - 1))
            result[:, : image.shape[1]] = image
            result[:, -image.shape[1] :] = image[:, ::-1]
        elif side == "l":
            result = np.zeros((image.shape[0], image.shape[1] * 2 - 1))
            result[:, : image.shape[1]] = image[:, ::-1]
            result[:, -image.shape[1] :] = image
        elif side == "b":
            result = np.zeros((image.shape[0] * 2 - 1, image.shape[1]))
            result[: image.shape[0], :] = image
            result[-image.shape[0] :, :] = image[::-1]
        elif side == "t":
            result = np.zeros((image.shape[0] * 2 - 1, image.shape[1]))
            result[: image.shape[0], :] = image[::-1]
            result[-image.shape[0] :, :] = image

        elif side == "rb":
            result = np.zeros((image.shape[0] * 2 - 1, image.shape[1] * 2 - 1))
            result[: image.shape[0], : image.shape[1]] = image
            result[: image.shape[0], -image.shape[1] :] = image[:, ::-1]
            result[-image.shape[0] :, : image.shape[1]] = image[::-1, :]
            result[-image.shape[0] :, -image.shape[1] :] = image[::-1, ::-1]

        elif side == "rt":
            result = np.zeros((image.shape[0] * 2 - 1, image.shape[1] * 2 - 1))
            result[: image.shape[0], : image.shape[1]] = image[::-1, :]
            result[: image.shape[0], -image.shape[1] :] = image[::-1, ::-1]
            result[-image.shape[0] :, : image.shape[1]] = image
            result[-image.shape[0] :, -image.shape[1] :] = image[:, ::-1]

        elif side == "lt":
            result = np.zeros((image.shape[0] * 2 - 1, image.shape[1] * 2 - 1))
            result[: image.shape[0], : image.shape[1]] = image[::-1, ::-1]
            result[: image.shape[0], -image.shape[1] :] = image[::-1, :]
            result[-image.shape[0] :, : image.shape[1]] = image[:, ::-1]
            result[-image.shape[0] :, -image.shape[1] :] = image

        elif side == "lb":
            result = np.zeros((image.shape[0] * 2 - 1, image.shape[1] * 2 - 1))
            result[: image.shape[0], : image.shape[1]] = image[:, ::-1]
            result[: image.shape[0], -image.shape[1] :] = image
            result[-image.shape[0] :, : image.shape[1]] = image[::-1, ::-1]
            result[-image.shape[0] :, -image.shape[1] :] = image[::-1, :]
    except:
        return 2, None

    return 0, result


def get_color(color_dict, colors):
    """ looks for the dict element of colors list, equals to color_dict"""
    for i, color in enumerate(colors):
        for data in color:
            equal = True
            for k, v in data.items():
                if k not in color_dict or v != color_dict[k]:
                    equal = False
                    break
            if equal:
                return i
    return -1