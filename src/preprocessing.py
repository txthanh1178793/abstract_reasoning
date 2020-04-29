import numpy as np
from scipy.stats import mode
from scipy import ndimage


def find_grid(image):
    # Looks for the grid in image and returns color and size
    grid_color = -1
    size = [0, 0]
    # TODO: border = False
    # TODO: bold_grid

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


def get_color_swap(image, color_1, color_2):
    """swapping two colors"""
    result = image.copy()
    result[image == color_1] = color_2
    result[image == color_2] = color_1
    return 0, result


def get_min_block(image):
    masks, n_masks = ndimage.label(image, structure=[[1, 1, 1], [1, 1, 1], [1, 1, 1]])
    sizes = [(masks == i).sum() for i in range(1, n_masks + 1)]

    if n_masks == 0:
        return 2, None

    min_n = np.argmin(sizes) + 1

    boundaries = find_color_boundaries(masks, min_n)
    if boundaries:
        return (
            0,
            image[boundaries[0] : boundaries[1] + 1, boundaries[2] : boundaries[3] + 1],
        )
    else:
        return 1, None


def get_max_block(image):
    masks, n_masks = ndimage.label(image, structure=[[1, 1, 1], [1, 1, 1], [1, 1, 1]])
    sizes = [(masks == i).sum() for i in range(1, n_masks + 1)]

    if n_masks == 0:
        return 2, None

    max_n = np.argmax(sizes) + 1

    boundaries = find_color_boundaries(masks, max_n)
    if boundaries:
        return (
            0,
            image[boundaries[0] : boundaries[1] + 1, boundaries[2] : boundaries[3] + 1],
        )
    else:
        return 1, None


def get_color(color_dict, colors):
    """ retrive the absolute number corresponding a color set by color_dict"""
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


def get_color_scheme(image):
    """processes original image and returns dict color scheme"""
    result = {
        "grid_color": -1,
        "colors": [[], [], [], [], [], [], [], [], [], []],
        "colors_sorted": [],
        "grid_size": [1, 1],
    }

    # preparing colors info

    unique, counts = np.uint8(np.unique(image, return_counts=True))
    colors = [unique[i] for i in np.argsort(counts)]

    result["colors_sorted"] = colors

    for color in range(10):
        # use abs color value - same for any image
        result["colors"][color].append({"type": "abs", "k": color})

    for k, color in enumerate(colors):
        # use k-th colour (sorted by presence on image)
        result["colors"][color].append({"type": "min", "k": k})
        # use k-th colour (sorted by presence on image)
        result["colors"][color].append({"type": "max", "k": len(colors) - k - 1})

    grid_color, grid_size = find_grid(image)
    if grid_color >= 0:
        result["grid_color"] = grid_color
        result["grid_size"] = grid_size
        result["colors"][grid_color].append({"type": "grid"})

    return result


def process_image(image, list_of_processors=None):
    """processes the original image and returns dict with structured image blocks"""
    if not list_of_processors:
        list_of_processors = []

    result = get_color_scheme(image)
    result["blocks"] = []

    # generating blocks

    # starting with the original image
    result["blocks"].append({"block": image, "params": []})

    # adding min and max blocks
    status, block = get_max_block(image)
    if status == 0 and block.shape[0] > 0 and block.shape[1] > 0:
        result["blocks"].append({"block": block, "params": [{"type": "max_block"}]})
    status, block = get_min_block(image)
    if status == 0 and block.shape[0] > 0 and block.shape[1] > 0:
        result["blocks"].append({"block": block, "params": [{"type": "min_block"}]})

    # adding the max area covered by each color
    for color in result["colors_sorted"]:
        status, block = get_color_max(image, color)
        if status == 0 and block.shape[0] > 0 and block.shape[1] > 0:
            for color_dict in result["colors"][color].copy():
                result["blocks"].append(
                    {
                        "block": block,
                        "params": [{"type": "color_max", "color": color_dict}],
                    }
                )

    # adding 'voting corners' block
    status, block = get_voting_corners(image, operation="rotate")
    if status == 0 and block.shape[0] > 0 and block.shape[1] > 0:
        result["blocks"].append(
            {
                "block": block,
                "params": [{"type": "voting_corners", "operation": "rotate"}],
            }
        )

    status, block = get_voting_corners(image, operation="reflect")
    if status == 0 and block.shape[0] > 0 and block.shape[1] > 0:
        result["blocks"].append(
            {
                "block": block,
                "params": [{"type": "voting_corners", "operation": "reflect"}],
            }
        )

    # adding grid cells
    if result["grid_color"] > 0:
        for i in range(result["grid_size"][0]):
            for j in range(result["grid_size"][1]):
                status, block = get_grid(image, result["grid_size"], (i, j))
                if status == 0 and block.shape[0] > 0 and block.shape[1] > 0:
                    result["blocks"].append(
                        {
                            "block": block,
                            "params": [
                                {
                                    "type": "grid",
                                    "grid_size": result["grid_size"],
                                    "cell": [i, j],
                                }
                            ],
                        }
                    )

    # adding halfs of the images
    for side in "lrtb":
        status, block = get_half(image, side=side)
        if status == 0 and block.shape[0] > 0 and block.shape[1] > 0:
            result["blocks"].append(
                {"block": block, "params": [{"type": "half", "side": side}]}
            )

    # rotate all blocks
    current_blocks = result["blocks"].copy()
    for k in range(1, 4):
        for data in current_blocks:
            status, block = get_rotation(data["block"], k=k)
            if status == 0 and block.shape[0] > 0 and block.shape[1] > 0:
                result["blocks"].append(
                    {
                        "block": block,
                        "params": data["params"] + [{"type": "rotation", "k": k}],
                    }
                )

    # transpose all blocks
    current_blocks = result["blocks"].copy()
    for data in current_blocks:
        status, block = get_transpose(data["block"])
        if status == 0 and block.shape[0] > 0 and block.shape[1] > 0:
            result["blocks"].append(
                {"block": block, "params": data["params"] + [{"type": "transpose"}]}
            )

    # cut_edgest for all blocks
    current_blocks = result["blocks"].copy()
    for l, r, t, b in [
        (1, 1, 1, 1),
        (1, 0, 0, 0),
        (0, 1, 0, 0),
        (0, 0, 1, 0),
        (0, 0, 0, 1),
        (1, 1, 0, 0),
        (1, 0, 0, 1),
        (0, 0, 1, 1),
        (0, 1, 1, 0),
    ]:
        for data in current_blocks:
            status, block = get_cut_edge(data["block"], l=l, r=r, t=t, b=b)
            if status == 0 and block.shape[0] > 0 and block.shape[1] > 0:
                result["blocks"].append(
                    {
                        "block": block,
                        "params": data["params"]
                        + [{"type": "cut_edge", "l": l, "r": r, "t": t, "b": b}],
                    }
                )

    # reflect all blocks
    current_blocks = result["blocks"].copy()
    for side in ["r", "l", "t", "b", "rt", "rb", "lt", "lb"]:
        for data in current_blocks:
            status, block = get_reflect(data["block"], side)
            if status == 0 and block.shape[0] > 0 and block.shape[1] > 0:
                result["blocks"].append(
                    {
                        "block": block,
                        "params": data["params"] + [{"type": "reflect", "side": side}],
                    }
                )

    # resize all blocks
    current_blocks = result["blocks"].copy()
    for scale in [2, 3]:
        for data in current_blocks:
            status, block = get_resize(data["block"], scale)
            if status == 0 and block.shape[0] > 0 and block.shape[1] > 0:
                result["blocks"].append(
                    {
                        "block": block,
                        "params": data["params"] + [{"type": "resize", "scale": scale}],
                    }
                )

    # swap some colors
    current_blocks = result["blocks"].copy()
    for i, color_1 in enumerate(result["colors_sorted"][:-1]):
        for color_2 in result["colors_sorted"][i:]:
            for data in current_blocks:
                status, block = get_color_swap(image, color_1, color_2)
                if status == 0 and block.shape[0] > 0 and block.shape[1] > 0:
                    for color_dict_1 in result["colors"][color_1].copy():
                        for color_dict_2 in result["colors"][color_2].copy():
                            result["blocks"].append(
                                {
                                    "block": block,
                                    "params": data["params"]
                                    + [
                                        {
                                            "type": "color_swap",
                                            "color_1": color_dict_1,
                                            "color_2": color_dict_2,
                                        }
                                    ],
                                }
                            )

    return result


def get_predict(image, transforms):
    """ applies the list of transforms to the image"""
    for transform in transforms:
        function = globals()["get_" + transform["type"]]
        params = transform.copy()
        params.pop("type")
        for color_name in ["color", "color_1", "color_2"]:
            if color_name in params:
                color_scheme = get_color_scheme(image)
                params[color_name] = get_color(
                    params[color_name], color_scheme["colors"]
                )
        status, image = function(image, **params)
        if status != 0:
            return 1, None
    return 0, image


def preprocess_sample(sample):
    """ make the whole preprocessing for particular sample"""
    sample["processed_train"] = []

    original_image = np.array(sample["train"][0]["input"])
    sample["processed_train"].append(process_image(original_image))

    for image in sample["train"][1:]:
        original_image = np.array(image["input"])
        sample["processed_train"].append(get_color_scheme(original_image))
    return sample
