import json
import time

import numpy as np

from scipy import ndimage
from scipy.stats import mode
from src.utils import matrix2answer


def find_grid(image, frame=False, possible_colors=None):
    """Looks for the grid in image and returns color and size"""
    grid_color = -1
    size = [1, 1]

    if possible_colors is None:
        possible_colors = list(range(10))

    for color in possible_colors:
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

    if grid_color == -1 and not frame:
        color_candidate = image[0, 0]
        if (
            (image[0] == color_candidate).all()
            and (image[-1] == color_candidate).all()
            and (image[:, -1] == color_candidate).all()
            and (image[:, 0] == color_candidate).all()
        ):
            grid_color, size, _ = find_grid(
                image[1 : image.shape[0] - 1, 1 : image.shape[1] - 1], frame=True, possible_colors=[color_candidate]
            )
            return grid_color, size, frame
        else:
            return grid_color, size, frame

    return grid_color, size, frame


def find_color_boundaries(array, color):
    """Looks for the boundaries of any color and returns them"""
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
    """Returns the part of the image inside the color boundaries"""
    boundaries = find_color_boundaries(image, color)
    if boundaries:
        return (0, image[boundaries[0] : boundaries[1] + 1, boundaries[2] : boundaries[3] + 1])
    else:
        return 1, None


def get_pixel(image, i, j):
    """Returns the pixel by coordinates"""
    if i >= image.shape[0] or j >= image.shape[1]:
        return 1, None
    return 0, image[i : i + 1, j : j + 1]


def get_pixel_fixed(image, i):
    return 0, np.array([[i]])


def get_grid(image, grid_size, cell, frame=False):
    """ returns the particular cell form the image with grid"""
    if frame:
        return get_grid(image[1 : image.shape[0] - 1, 1 : image.shape[1] - 1], grid_size, cell, frame=False)
    if cell[0] >= grid_size[0] or cell[1] >= grid_size[1]:
        return 1, None
    steps = ((image.shape[0] + 1) // grid_size[0], (image.shape[1] + 1) // grid_size[1])
    block = image[steps[0] * cell[0] : steps[0] * (cell[0] + 1) - 1, steps[1] * cell[1] : steps[1] * (cell[1] + 1) - 1]
    return 0, block


def get_half(image, side):
    """ returns the half of the image"""
    if side not in ["l", "r", "t", "b", "long1", "long2"]:
        return 1, None
    if side == "l":
        return 0, image[:, : (image.shape[1]) // 2]
    elif side == "r":
        return 0, image[:, -((image.shape[1]) // 2) :]
    elif side == "b":
        return 0, image[-((image.shape[0]) // 2) :, :]
    elif side == "t":
        return 0, image[: (image.shape[0]) // 2, :]
    elif side == "long1":
        if image.shape[0] >= image.shape[1]:
            return get_half(image, "t")
        else:
            return get_half(image, "l")
    elif side == "long2":
        if image.shape[0] >= image.shape[1]:
            return get_half(image, "b")
        else:
            return get_half(image, "r")


def get_corner(image, side):
    """ returns the half of the image"""
    if side not in ["tl", "tr", "bl", "br"]:
        return 1, None
    size = (image.shape[0]) // 2, (image.shape[1]) // 2
    if side == "tl":
        return 0, image[size[0] :, -size[1] :]
    if side == "tr":
        return 0, image[size[0] :, : size[1]]
    if side == "bl":
        return 0, image[: -size[0], : size[1]]
    if side == "br":
        return 0, image[: -size[0], -size[1] :]


def get_k_part(image, num, k):
    if image.shape[0] > image.shape[1]:
        max_axis = 0
        max_shape = image.shape[0]
    else:
        max_axis = 1
        max_shape = image.shape[1]

    if max_shape % num != 0:
        return 1, None
    size = max_shape // num

    if max_axis == 0:
        return 0, image[k * size : (k + 1) * size]
    else:
        return 0, image[:, k * size : (k + 1) * size]


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
    if isinstance(scale, int):
        if image.shape[0] % scale != 0 or image.shape[1] % scale != 0:
            return 1, None
        if image.shape[0] < scale or image.shape[1] < scale:
            return 2, None

        arrays = []
        size = image.shape[0] // scale, image.shape[1] // scale
        for i in range(scale):
            for j in range(scale):
                arrays.append(image[i::scale, j::scale])

        result = mode(np.stack(arrays), axis=0).mode[0]
    else:
        size = int(image.shape[0] / scale), int(image.shape[1] / scale)
        result = []
        for i in range(size[0]):
            result.append([])
            for j in range(size[1]):
                result[-1].append(image[int(i * scale), int(j * scale)])

        result = np.uint8(result)

    return 0, result


def get_resize_to(image, size_x, size_y):
    """ resizes image according to scale"""
    scale_x = image.shape[0] // size_x
    scale_y = image.shape[1] // size_y
    if scale_x == 0 or scale_y == 0:
        return 3, None
    if image.shape[0] % scale_x != 0 or image.shape[1] % scale_y != 0:
        return 1, None
    if image.shape[0] < scale_x or image.shape[1] < scale_y:
        return 2, None

    arrays = []
    for i in range(scale_x):
        for j in range(scale_y):
            arrays.append(image[i::scale_x, j::scale_y])

    result = mode(np.stack(arrays), axis=0).mode[0]
    if result.max() > 10:
        print(1)

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
    if not (image == color_1).any() and not (image == color_2).any():
        return 1, None
    result = image.copy()
    result[image == color_1] = color_2
    result[image == color_2] = color_1
    return 0, result


def get_cut(image, x1, y1, x2, y2):
    if x1 >= x2 or y1 >= y2:
        return 1, None
    else:
        return 0, image[x1:x2, y1:y2]


def get_min_block(image, full=True):
    if full:
        structure = [[1, 1, 1], [1, 1, 1], [1, 1, 1]]
    else:
        structure = [[0, 1, 0], [1, 1, 1], [0, 1, 0]]
    masks, n_masks = ndimage.label(image, structure=structure)
    sizes = [(masks == i).sum() for i in range(1, n_masks + 1)]

    if n_masks == 0:
        return 2, None

    min_n = np.argmin(sizes) + 1

    boundaries = find_color_boundaries(masks, min_n)
    if boundaries:
        return (0, image[boundaries[0] : boundaries[1] + 1, boundaries[2] : boundaries[3] + 1])
    else:
        return 1, None


def get_min_block_mask(image, full=True):
    if full:
        structure = [[1, 1, 1], [1, 1, 1], [1, 1, 1]]
    else:
        structure = [[0, 1, 0], [1, 1, 1], [0, 1, 0]]
    masks, n_masks = ndimage.label(image, structure=structure)
    sizes = [(masks == i).sum() for i in range(1, n_masks + 1)]

    if n_masks == 0:
        return 2, None

    min_n = np.argmin(sizes) + 1
    return 0, masks == min_n


def get_max_block_mask(image, full=True):
    if full:
        structure = [[1, 1, 1], [1, 1, 1], [1, 1, 1]]
    else:
        structure = [[0, 1, 0], [1, 1, 1], [0, 1, 0]]
    masks, n_masks = ndimage.label(image, structure=structure)
    sizes = [(masks == i).sum() for i in range(1, n_masks + 1)]

    if n_masks == 0:
        return 2, None

    min_n = np.argmax(sizes) + 1
    return 0, masks == min_n


def get_max_block(image, full=True):
    if full:
        structure = [[1, 1, 1], [1, 1, 1], [1, 1, 1]]
    else:
        structure = [[0, 1, 0], [1, 1, 1], [0, 1, 0]]
    masks, n_masks = ndimage.label(image, structure=structure)
    sizes = [(masks == i).sum() for i in range(1, n_masks + 1)]

    if n_masks == 0:
        return 2, None

    max_n = np.argmax(sizes) + 1

    boundaries = find_color_boundaries(masks, max_n)
    if boundaries:
        return (0, image[boundaries[0] : boundaries[1] + 1, boundaries[2] : boundaries[3] + 1])
    else:
        return 1, None


def get_block_with_side_colors(image, block_type="min", structure=0):
    if structure == 0:
        structure = [[1, 1, 1], [1, 1, 1], [1, 1, 1]]
    else:
        structure = [[0, 1, 0], [1, 1, 1], [0, 1, 0]]
    masks, n_masks = ndimage.label(image, structure=structure)

    if n_masks == 0:
        return 2, None

    unique_nums = []
    for i in range(1, n_masks + 1):
        unique = np.unique(image[masks == i])
        unique_nums.append(len(unique))

    if block_type == "min":
        n = np.argmin(unique_nums) + 1
    else:
        n = np.argmax(unique_nums) + 1

    boundaries = find_color_boundaries(masks, n)
    if boundaries:
        return (0, image[boundaries[0] : boundaries[1] + 1, boundaries[2] : boundaries[3] + 1])
    else:
        return 1, None


def get_block_with_side_colors_count(image, block_type="min", structure=0):
    if structure == 0:
        structure = [[1, 1, 1], [1, 1, 1], [1, 1, 1]]
    else:
        structure = [[0, 1, 0], [1, 1, 1], [0, 1, 0]]
    masks, n_masks = ndimage.label(image, structure=structure)
    if n_masks == 0:
        return 2, None

    unique_nums = []
    for i in range(1, n_masks + 1):
        unique, counts = np.unique(image[masks == i], return_counts=True)
        unique_nums.append(min(counts))

    if block_type == "min":
        n = np.argmin(unique_nums) + 1
    else:
        n = np.argmax(unique_nums) + 1

    boundaries = find_color_boundaries(masks, n)
    if boundaries:
        return (0, image[boundaries[0] : boundaries[1] + 1, boundaries[2] : boundaries[3] + 1])
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


def get_mask_from_block(image, color):
    if color in np.unique(image, return_counts=False):
        return 0, image == color
    else:
        return 1, None


def get_background(image, color):
    return 0, np.uint8(np.ones_like(image) * color)


def get_mask_from_max_color_coverage(image, color):
    if color in np.unique(image, return_counts=False):
        boundaries = find_color_boundaries(image, color)
        result = (image.copy() * 0).astype(bool)
        result[boundaries[0] : boundaries[1] + 1, boundaries[2] : boundaries[3] + 1] = True
        return 0, image == color
    else:
        return 1, None


def add_unique_colors(image, result, colors=None):
    """adds information about colors unique for some parts of the image"""
    if colors is None:
        colors = np.unique(image)

    unique_side = [False for i in range(10)]
    unique_corner = [False for i in range(10)]

    half_size = (((image.shape[0] + 1) // 2), ((image.shape[1] + 1) // 2))
    for (image_part, side, unique_list) in [
        (image[: half_size[0]], "bottom", unique_side),
        (image[-half_size[0] :], "top", unique_side),
        (image[:, : half_size[1]], "right", unique_side),
        (image[:, -half_size[1] :], "left", unique_side),
        (image[-half_size[0] :, -half_size[1] :], "tl", unique_corner),
        (image[-half_size[0] :, : half_size[1]], "tr", unique_corner),
        (image[: half_size[0], : half_size[1]], "br", unique_corner),
        (image[: half_size[0], -half_size[1] :], "left", unique_corner),
    ]:
        unique = np.uint8(np.unique(image_part))
        if len(unique) == len(colors) - 1:
            color = [x for x in colors if x not in unique][0]
            unique_list[color] = True
            result["colors"][color].append({"type": "unique", "side": side})

    for i in range(10):
        if unique_corner[i]:
            result["colors"][i].append({"type": "unique", "side": "corner"})
        if unique_side[i]:
            result["colors"][i].append({"type": "unique", "side": "side"})
        if unique_side[i] or unique_corner[i]:
            result["colors"][i].append({"type": "unique", "side": "any"})

    return


def add_center_color(image, result, colors=None):
    i = image.shape[0] // 4
    j = image.shape[1] // 4
    center = image[i : image.shape[0] - i, j : image.shape[1] - j]
    values, counts = np.unique(center, return_counts=True)
    if len(counts) > 0:
        ind = np.argmax(counts)
        color = values[ind]
        result["colors"][color].append({"type": "center"})


def get_color_scheme(image, target_image=None, params=None):
    """processes original image and returns dict color scheme"""
    result = {
        "grid_color": -1,
        "colors": [[], [], [], [], [], [], [], [], [], []],
        "colors_sorted": [],
        "grid_size": [1, 1],
    }

    if params is None:
        params = ["coverage", "unique", "corners", "top", "grid"]

    # preparing colors info

    unique, counts = np.unique(image, return_counts=True)
    colors = [unique[i] for i in np.argsort(counts)]

    result["colors_sorted"] = colors
    result["colors_num"] = len(colors)

    for color in range(10):
        # use abs color value - same for any image
        result["colors"][color].append({"type": "abs", "k": color})

    if len(colors) == 2 and 0 in colors:
        result["colors"][[x for x in colors if x != 0][0]].append({"type": "non_zero"})

    if "coverage" in params:
        for k, color in enumerate(colors):
            # use k-th colour (sorted by presence on image)
            result["colors"][color].append({"type": "min", "k": k})
            # use k-th colour (sorted by presence on image)
            result["colors"][color].append({"type": "max", "k": len(colors) - k - 1})

    if "unique" in params:
        add_unique_colors(image, result, colors=None)
        add_center_color(image, result)

    if "corners" in params:
        # colors in the corners of images
        result["colors"][image[0, 0]].append({"type": "corner", "side": "tl"})
        result["colors"][image[0, -1]].append({"type": "corner", "side": "tr"})
        result["colors"][image[-1, 0]].append({"type": "corner", "side": "bl"})
        result["colors"][image[-1, -1]].append({"type": "corner", "side": "br"})

    if "top" in params:
        # colors that are on top of other and have full vertical on horizontal line
        for k in range(10):
            mask = image == k
            is_on_top0 = mask.min(axis=0).any()
            is_on_top1 = mask.min(axis=1).any()
            if is_on_top0:
                result["colors"][k].append({"type": "on_top", "side": "0"})
            if is_on_top1:
                result["colors"][k].append({"type": "on_top", "side": "1"})
            if is_on_top1 or is_on_top0:
                result["colors"][k].append({"type": "on_top", "side": "any"})

    if "grid" in params:
        grid_color, grid_size, frame = find_grid(image)
        if grid_color >= 0:
            result["grid_color"] = grid_color
            result["grid_size"] = grid_size
            result["grid_frame"] = frame
            result["colors"][grid_color].append({"type": "grid"})

    return result


def add_block(target_dict, image, params_list):
    array_hash = hash(matrix2answer(image))
    if array_hash not in target_dict["arrays"]:
        target_dict["arrays"][array_hash] = {"array": image, "params": []}

    for params in params_list:
        params_hash = get_dict_hash(params)
        target_dict["arrays"][array_hash]["params"].append(params)
        target_dict["params"][params_hash] = array_hash


def get_original(image):
    return 0, image


def get_inversed_colors(image):
    unique = np.unique(image)
    if len(unique) != 2:
        return 1, None
    result = image.copy()
    result[image == unique[0]] = unique[1]
    result[image == unique[1]] = unique[0]
    return 0, result


def generate_blocks(image, result, max_time=600, max_blocks=200000, max_masks=200000, target_image=None, params=None):
    all_params = [
        "initial",
        "background",
        "min_max_blocks",
        "block_with_side_colors",
        "max_area_covered",
        "grid_cells",
        "halves",
        "corners",
        "rotate",
        "transpose",
        "cut_edges",
        "resize",
        "reflect",
        "cut_parts",
        "swap_colors",
        "k_part",
    ]

    if not params:
        params = all_params

    start_time = time.time()

    result["blocks"] = {"arrays": {}, "params": {}}

    if "initial" in params:
        # starting with the original image
        add_block(result["blocks"], image, [[{"type": "original"}]])

        # inverse colors
        status, block = get_inversed_colors(image)
        if status == 0 and block.shape[0] > 0 and block.shape[1] > 0:
            add_block(result["blocks"], block, [[{"type": "inversed_colors"}]])

    # adding min and max blocks
    if (
        ("min_max_blocks" in params)
        and (time.time() - start_time < max_time)
        and (len(result["blocks"]["arrays"]) < max_blocks)
    ):
        # print("min_max_blocks")
        for full in [True, False]:
            status, block = get_max_block(image, full)
            if status == 0 and block.shape[0] > 0 and block.shape[1] > 0:
                add_block(result["blocks"], block, [[{"type": "max_block", "full": full}]])

    if (
        ("block_with_side_colors" in params)
        and (time.time() - start_time < max_time)
        and (len(result["blocks"]["arrays"]) < max_blocks)
    ):
        # print("min_max_blocks")
        for block_type in ["min", "max"]:
            for structure in [0, 1]:
                status, block = get_block_with_side_colors(image, block_type, structure)
                if status == 0 and block.shape[0] > 0 and block.shape[1] > 0:
                    add_block(
                        result["blocks"],
                        block,
                        [[{"type": "block_with_side_colors", "block_type": block_type, "structure": structure}]],
                    )
        for block_type in ["min", "max"]:
            for structure in [0, 1]:
                status, block = get_block_with_side_colors_count(image, block_type, structure)
                if status == 0 and block.shape[0] > 0 and block.shape[1] > 0:
                    add_block(
                        result["blocks"],
                        block,
                        [[{"type": "block_with_side_colors_count", "block_type": block_type, "structure": structure}]],
                    )
    # print(sum([len(x['params']) for x in result['blocks']['arrays'].values()]))
    # adding background
    if ("background" in params) and (time.time() - start_time < max_time):
        # print("background")
        for color in range(10):
            status, block = get_background(image, color)
            if status == 0 and block.shape[0] > 0 and block.shape[1] > 0:
                params_list = []
                for color_dict in result["colors"][color].copy():
                    params_list.append([{"type": "background", "color": color_dict}])
                add_block(result["blocks"], block, params_list)

    # adding the max area covered by each color
    if ("max_area_covered" in params) and (time.time() - start_time < max_time):
        # print("max_area_covered")
        for color in result["colors_sorted"]:
            status, block = get_color_max(image, color)
            if status == 0 and block.shape[0] > 0 and block.shape[1] > 0:
                params_list = []
                for color_dict in result["colors"][color].copy():
                    params_list.append([{"type": "color_max", "color": color_dict}])
                add_block(result["blocks"], block, params_list)

    # adding grid cells
    if (
        ("grid_cells" in params)
        and (time.time() - start_time < max_time)
        and (len(result["blocks"]["arrays"]) < max_blocks)
    ):
        if result["grid_color"] > 0:
            for i in range(result["grid_size"][0]):
                for j in range(result["grid_size"][1]):
                    status, block = get_grid(image, result["grid_size"], (i, j), frame=result["grid_frame"])
                    if status == 0 and block.shape[0] > 0 and block.shape[1] > 0:
                        add_block(
                            result["blocks"],
                            block,
                            [
                                [
                                    {
                                        "type": "grid",
                                        "grid_size": result["grid_size"],
                                        "cell": [i, j],
                                        "frame": result["grid_frame"],
                                    }
                                ]
                            ],
                        )

    # adding halves of the images
    if ("halves" in params) and (time.time() - start_time < max_time) and (len(result["blocks"]["arrays"]) < max_blocks):
        for side in ["l", "r", "t", "b", "long1", "long2"]:
            status, block = get_half(image, side=side)
            if status == 0 and block.shape[0] > 0 and block.shape[1] > 0:
                add_block(result["blocks"], block, [[{"type": "half", "side": side}]])

    # extracting pixels from image
    if ("pixels" in params) and (time.time() - start_time < max_time) and (len(result["blocks"]["arrays"]) < max_blocks):
        for i in range(image.shape[0]):
            for j in range(image.shape[1]):
                status, block = get_pixel(image, i=i, j=j)
                if status == 0 and block.shape[0] > 0 and block.shape[1] > 0:
                    add_block(result["blocks"], block, [[{"type": "pixel", "i": i, "j": j}]])

    # extracting pixels from image
    if (
        ("pixel_fixed" in params)
        and (time.time() - start_time < max_time)
        and (len(result["blocks"]["arrays"]) < max_blocks)
    ):
        for i in range(10):
            status, block = get_pixel_fixed(image, i=i)
            if status == 0 and block.shape[0] > 0 and block.shape[1] > 0:
                add_block(result["blocks"], block, [[{"type": "pixel_fixed", "i": i}]])

    # adding halves of the images
    if ("k_part" in params) and (time.time() - start_time < max_time) and (len(result["blocks"]["arrays"]) < max_blocks):
        for num in [3, 4]:
            for k in range(num):
                status, block = get_k_part(image, num=num, k=k)
                if status == 0 and block.shape[0] > 0 and block.shape[1] > 0:
                    add_block(result["blocks"], block, [[{"type": "k_part", "num": num, "k": k}]])

    # adding corners of the images
    if (
        ("corners" in params)
        and (time.time() - start_time < max_time)
        and (len(result["blocks"]["arrays"]) < max_blocks)
    ):
        for side in ["tl", "tr", "bl", "br"]:
            status, block = get_corner(image, side=side)
            if status == 0 and block.shape[0] > 0 and block.shape[1] > 0:
                add_block(result["blocks"], block, [[{"type": "corner", "side": side}]])

    main_blocks_num = len(result["blocks"])

    # rotate all blocks
    if ("rotate" in params) and (time.time() - start_time < max_time) and (len(result["blocks"]["arrays"]) < max_blocks):
        current_blocks = result["blocks"]["arrays"].copy()
        for k in range(1, 4):
            for key, data in current_blocks.items():
                status, block = get_rotation(data["array"], k=k)
                if status == 0 and block.shape[0] > 0 and block.shape[1] > 0:
                    params_list = [i + [{"type": "rotation", "k": k}] for i in data["params"]]
                    add_block(result["blocks"], block, params_list)

    # transpose all blocks
    if (
        ("transpose" in params)
        and (time.time() - start_time < max_time)
        and (len(result["blocks"]["arrays"]) < max_blocks)
    ):
        current_blocks = result["blocks"]["arrays"].copy()
        for key, data in current_blocks.items():
            status, block = get_transpose(data["array"])
            if status == 0 and block.shape[0] > 0 and block.shape[1] > 0:
                params_list = [i + [{"type": "transpose"}] for i in data["params"]]
                add_block(result["blocks"], block, params_list)

    # cut edges for all blocks
    if (
        ("cut_edges" in params)
        and (time.time() - start_time < max_time)
        and (len(result["blocks"]["arrays"]) < max_blocks)
    ):
        current_blocks = result["blocks"]["arrays"].copy()
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
            if time.time() - start_time < max_time:
                for key, data in current_blocks.items():
                    status, block = get_cut_edge(data["array"], l=l, r=r, t=t, b=b)
                    if status == 0 and block.shape[0] > 0 and block.shape[1] > 0:
                        params_list = [
                            i + [{"type": "cut_edge", "l": l, "r": r, "t": t, "b": b}] for i in data["params"]
                        ]
                        add_block(result["blocks"], block, params_list)

    # resize all blocks
    if ("resize" in params) and (time.time() - start_time < max_time) and (len(result["blocks"]["arrays"]) < max_blocks):
        current_blocks = result["blocks"]["arrays"].copy()
        for scale in [2, 3, 1 / 2, 1 / 3]:
            for key, data in current_blocks.items():
                status, block = get_resize(data["array"], scale)
                if status == 0 and block.shape[0] > 0 and block.shape[1] > 0:
                    params_list = [i + [{"type": "resize", "scale": scale}] for i in data["params"]]
                    add_block(result["blocks"], block, params_list)

        for size_x, size_y in [(2, 2), (3, 3)]:
            for key, data in current_blocks.items():
                status, block = get_resize_to(data["array"], size_x, size_y)
                if status == 0 and block.shape[0] > 0 and block.shape[1] > 0:
                    params_list = [
                        i + [{"type": "resize_to", "size_x": size_x, "size_y": size_y}] for i in data["params"]
                    ]
                    add_block(result["blocks"], block, params_list)

    # reflect all blocks
    if (
        ("reflect" in params)
        and (time.time() - start_time < max_time)
        and (len(result["blocks"]["arrays"]) < max_blocks)
    ):
        current_blocks = result["blocks"]["arrays"].copy()
        for side in ["r", "l", "t", "b", "rt", "rb", "lt", "lb"]:
            if time.time() - start_time < max_time:
                for key, data in current_blocks.items():
                    status, block = get_reflect(data["array"], side)
                    if status == 0 and block.shape[0] > 0 and block.shape[1] > 0:
                        params_list = [i + [{"type": "reflect", "side": side}] for i in data["params"]]
                        add_block(result["blocks"], block, params_list)

    # cut some parts of images
    if (
        ("cut_parts" in params)
        and (time.time() - start_time < max_time)
        and (len(result["blocks"]["arrays"]) < max_blocks)
    ):
        max_x = image.shape[0]
        max_y = image.shape[1]
        min_block_size = 2
        for x1 in range(0, max_x - min_block_size):
            if time.time() - start_time < max_time:
                if max_x - x1 <= min_block_size:
                    continue
                for x2 in range(x1 + min_block_size, max_x):
                    for y1 in range(0, max_y - min_block_size):
                        if max_y - y1 <= min_block_size:
                            continue
                        for y2 in range(y1 + min_block_size, max_y):
                            status, block = get_cut(image, x1, y1, x2, y2)
                            if status == 0:
                                add_block(
                                    result["blocks"], block, [[{"type": "cut", "x1": x1, "x2": x2, "y1": y1, "y2": y2}]]
                                )

    list_param_list = []
    list_blocks = []

    # swap some colors
    if (
        ("swap_colors" in params)
        and (time.time() - start_time < max_time)
        and (len(result["blocks"]["arrays"]) < max_blocks)
    ):
        current_blocks = result["blocks"]["arrays"].copy()
        for color_1 in range(9):
            if time.time() - start_time < max_time:
                for color_2 in range(color_1 + 1, 10):
                    for key, data in current_blocks.items():
                        status, block = get_color_swap(data["array"], color_1, color_2)
                        if status == 0 and block.shape[0] > 0 and block.shape[1] > 0:
                            for color_dict_1 in result["colors"][color_1].copy():
                                for color_dict_2 in result["colors"][color_2].copy():
                                    list_param_list.append(
                                        [
                                            j
                                            + [{"type": "color_swap", "color_1": color_dict_1, "color_2": color_dict_2}]
                                            for j in data["params"]
                                        ]
                                    )
                                    list_blocks.append(block)

    for block, params_list in zip(list_blocks, list_param_list):
        add_block(result["blocks"], block, params_list)

    if time.time() - start_time > max_time:
        print("Time is over")
    if len(result["blocks"]["arrays"]) >= max_blocks:
        print("Max number of blocks exceeded")
    return result


def generate_masks(image, result, max_time=600, max_blocks=200000, max_masks=200000, target_image=None, params=None):
    start_time = time.time()

    all_params = ["initial_masks", "additional_masks", "coverage_masks", "min_max_masks"]

    if not params:
        params = all_params

    result["masks"] = {"arrays": {}, "params": {}}

    # making one mask for each generated block
    current_blocks = result["blocks"]["arrays"].copy()
    if ("initial_masks" in params) and (time.time() - start_time < max_time * 2):
        for key, data in current_blocks.items():
            for color in result["colors_sorted"]:
                status, mask = get_mask_from_block(data["array"], color)
                if status == 0 and mask.shape[0] > 0 and mask.shape[1] > 0:
                    params_list = [
                        {"operation": "none", "params": {"block": i, "color": color_dict}}
                        for i in data["params"]
                        for color_dict in result["colors"][color]
                    ]
                    add_block(result["masks"], mask, params_list)

    initial_masks = result["masks"]["arrays"].copy()
    if ("initial_masks" in params) and (time.time() - start_time < max_time * 2):
        for key, mask in initial_masks.items():
            add_block(
                result["masks"],
                np.logical_not(mask["array"]),
                [{"operation": "not", "params": param["params"]} for param in mask["params"]],
            )

    initial_masks = result["masks"]["arrays"].copy()
    masks_to_add = []
    processed = []
    if ("additional_masks" in params) and (time.time() - start_time < max_time * 2):
        for key1, mask1 in initial_masks.items():
            processed.append(key1)
            if time.time() - start_time < max_time * 2 and (
                target_image is None
                or (target_image.shape == mask1["array"].shape)
                or (target_image.shape == mask1["array"].T.shape)
            ):
                for key2, mask2 in initial_masks.items():
                    if key2 in processed:
                        continue
                    if (mask1["array"].shape[0] == mask2["array"].shape[0]) and (
                        mask1["array"].shape[1] == mask2["array"].shape[1]
                    ):
                        params_list_and = []
                        params_list_or = []
                        params_list_xor = []
                        for param1 in mask1["params"]:
                            for param2 in mask2["params"]:
                                params_list_and.append(
                                    {"operation": "and", "params": {"mask1": param1, "mask2": param2}}
                                )
                                params_list_or.append({"operation": "or", "params": {"mask1": param1, "mask2": param2}})
                                params_list_xor.append(
                                    {"operation": "xor", "params": {"mask1": param1, "mask2": param2}}
                                )
                        masks_to_add.append(
                            (result["masks"], np.logical_and(mask1["array"], mask2["array"]), params_list_and)
                        )
                        masks_to_add.append(
                            (result["masks"], np.logical_or(mask1["array"], mask2["array"]), params_list_or)
                        )
                        masks_to_add.append(
                            (result["masks"], np.logical_xor(mask1["array"], mask2["array"]), params_list_xor)
                        )

    for path, array, params_list in masks_to_add:
        add_block(path, array, params_list)
    # coverage_masks
    if ("coverage_masks" in params) and (time.time() - start_time < max_time * 2):
        for color in result["colors_sorted"][1:]:
            status, mask = get_mask_from_max_color_coverage(image, color)
            if status == 0 and mask.shape[0] > 0 and mask.shape[1] > 0:
                params_list = [
                    {"operation": "coverage", "params": {"color": color_dict}}
                    for color_dict in result["colors"][color].copy()
                ]
                add_block(result["masks"], mask, params_list)
    # coverage_masks
    if ("min_max_masks" in params) and (time.time() - start_time < max_time * 2):
        status, mask = get_min_block_mask(image)
        if status == 0 and mask.shape[0] > 0 and mask.shape[1] > 0:
            params_list = [{"operation": "min_block"}]
            add_block(result["masks"], mask, params_list)
        status, mask = get_max_block_mask(image)
        if status == 0 and mask.shape[0] > 0 and mask.shape[1] > 0:
            params_list = [{"operation": "max_block"}]
            add_block(result["masks"], mask, params_list)
    if time.time() - start_time > max_time:
        print("Time is over")
    if len(result["blocks"]["arrays"]) >= max_masks:
        print("Max number of masks exceeded")
    return result


def process_image(
    image, max_time=600, max_blocks=200000, max_masks=200000, target_image=None, params=None, color_params=None
):
    """processes the original image and returns dict with structured image blocks"""

    result = get_color_scheme(image, target_image=target_image, params=color_params)
    result = generate_blocks(image, result, max_time, max_blocks, max_masks, target_image, params, color_params)
    result = generate_masks(image, result, max_time, max_blocks, max_masks, target_image, params, color_params)

    return result


def get_mask_from_block_params(image, params, block_cache=None, mask_cache=None, color_scheme=None):
    if mask_cache is None:
        mask_cache = {{"arrays": {}, "params": {}}}
    dict_hash = get_dict_hash(params)
    if dict_hash in mask_cache:
        mask = mask_cache["arrays"][mask_cache["params"][dict_hash]]["array"]
        if len(mask) == 0:
            return 1, None
        else:
            return 0, mask

    if params["operation"] == "none":
        status, block = get_predict(image, params["params"]["block"], block_cache, color_scheme)
        if status != 0:
            add_block(mask_cache, np.array([[]]), [params])
            return 1, None
        if not color_scheme:
            color_scheme = get_color_scheme(image)
        color_num = get_color(params["params"]["color"], color_scheme["colors"])
        if color_num < 0:
            add_block(mask_cache, np.array([[]]), [params])
            return 2, None
        status, mask = get_mask_from_block(block, color_num)
        if status != 0:
            add_block(mask_cache, np.array([[]]), [params])
            return 6, None
        add_block(mask_cache, mask, [params])
        return 0, mask
    elif params["operation"] == "not":
        new_params = params.copy()
        new_params["operation"] = "none"
        status, mask = get_mask_from_block_params(
            image, new_params, block_cache=block_cache, color_scheme=color_scheme, mask_cache=mask_cache
        )
        if status != 0:
            add_block(mask_cache, np.array([[]]), [params])
            return 3, None
        mask = np.logical_not(mask)
        add_block(mask_cache, mask, [params])
        return 0, mask
    elif params["operation"] in ["and", "or", "xor"]:
        new_params = params["params"]["mask1"]
        status, mask1 = get_mask_from_block_params(
            image, new_params, block_cache=block_cache, color_scheme=color_scheme, mask_cache=mask_cache
        )
        if status != 0:
            add_block(mask_cache, np.array([[]]), [params])
            return 4, None
        new_params = params["params"]["mask2"]
        status, mask2 = get_mask_from_block_params(
            image, new_params, block_cache=block_cache, color_scheme=color_scheme, mask_cache=mask_cache
        )
        if status != 0:
            add_block(mask_cache, np.array([[]]), [params])
            return 5, None
        if mask1.shape[0] != mask2.shape[0] or mask1.shape[1] != mask2.shape[1]:
            add_block(mask_cache, np.array([[]]), [params])
            return 6, None
        if params["operation"] == "and":
            mask = np.logical_and(mask1, mask2)
        elif params["operation"] == "or":
            mask = np.logical_or(mask1, mask2)
        elif params["operation"] == "xor":
            mask = np.logical_xor(mask1, mask2)
        add_block(mask_cache, mask, [params])
        return 0, mask
    elif params["operation"] == "coverage":
        if not color_scheme:
            color_scheme = get_color_scheme(image)
        color_num = get_color(params["params"]["color"], color_scheme["colors"])
        if color_num < 0:
            add_block(mask_cache, np.array([[]]), [params])
            return 2, None
        status, mask = get_mask_from_max_color_coverage(image, color_num)
        if status != 0:
            add_block(mask_cache, np.array([[]]), [params])
            return 6, None
        add_block(mask_cache, mask, [params])
        return 0, mask
    elif params["operation"] == "min_block":
        status, mask = get_min_block_mask(image)
        if status != 0:
            add_block(mask_cache, np.array([[]]), [params])
            return 6, None
        add_block(mask_cache, mask, [params])
        return 0, mask
    elif params["operation"] == "max_block":
        status, mask = get_max_block_mask(image)
        if status != 0:
            add_block(mask_cache, np.array([[]]), [params])
            return 6, None
        add_block(mask_cache, mask, [params])
        return 0, mask


def get_dict_hash(d):
    return hash(json.dumps(d, sort_keys=True))


def get_predict(image, transforms, block_cache=None, color_scheme=None):
    """ applies the list of transforms to the image"""
    params_hash = get_dict_hash(transforms)
    if params_hash in block_cache["params"]:
        if block_cache["params"][params_hash] is None:
            return 1, None
        else:
            return 0, block_cache["arrays"][block_cache["params"][params_hash]]["array"]

    if not color_scheme:
        color_scheme = get_color_scheme(image)

    if len(transforms) > 1:
        status, previous_image = get_predict(image, transforms[:-1], block_cache=block_cache, color_scheme=color_scheme)
        if status != 0:
            return status, None
    else:
        previous_image = image

    transform = transforms[-1]
    function = globals()["get_" + transform["type"]]
    params = transform.copy()
    params.pop("type")
    for color_name in ["color", "color_1", "color_2"]:
        if color_name in params:
            params[color_name] = get_color(params[color_name], color_scheme["colors"])
            if params[color_name] < 0:
                return 2, None
    status, result = function(previous_image, **params)

    if status != 0 or len(result) == 0 or len(result[0]) == 0:
        block_cache["params"][params_hash] = None
        return 1, None

    add_block(block_cache, result, [transforms])
    return 0, result


def filter_colors(sample):
    # filtering colors, that are not present in at least one of the images
    all_colors = []
    for color_scheme1 in sample["train"]:
        list_of_colors = [get_dict_hash(color_dict) for i in range(10) for color_dict in color_scheme1["colors"][i]]
        all_colors.append(list_of_colors)
    for j in range(1, len(sample["train"])):
        all_colors[0] = [x for x in all_colors[0] if x in all_colors[j]]
    keep_colors = set(all_colors[0])

    for color_scheme1 in sample["train"]:
        for i in range(10):
            j = 0
            while j < len(color_scheme1["colors"][i]):
                if get_dict_hash(color_scheme1["colors"][i][j]) in keep_colors:
                    j += 1
                else:
                    del color_scheme1["colors"][i][j]

    delete_colors = []
    color_scheme0 = sample["train"][0]
    for i in range(10):
        if len(color_scheme0["colors"][i]) > 1:
            for j, color_dict1 in enumerate(color_scheme0["colors"][i][::-1][:-1]):
                hash1 = get_dict_hash(color_dict1)
                delete = True
                for color_dict2 in color_scheme0["colors"][i][::-1][j + 1 :]:
                    hash2 = get_dict_hash(color_dict2)
                    for color_scheme1 in list(sample["train"][1:]) + list(sample["test"]):
                        found = False
                        for k in range(10):
                            hash_array = [get_dict_hash(color_dict) for color_dict in color_scheme1["colors"][k]]
                            if hash1 in hash_array and hash2 in hash_array:
                                found = True
                                break
                        if not found:
                            delete = False
                            break
                    if delete:
                        delete_colors.append(hash1)
                        break

    for color_scheme1 in sample["train"]:
        for i in range(10):
            j = 0
            while j < len(color_scheme1["colors"][i]):
                if get_dict_hash(color_scheme1["colors"][i][j]) in delete_colors:
                    del color_scheme1["colors"][i][j]
                else:
                    j += 1
    return


def filter_blocks(sample, arrays_type="blocks"):
    delete_blocks = []
    list_of_lists_of_sets = []
    for arrays_list in [x[arrays_type]["arrays"].values() for x in sample["train"][1:]] + [
        x[arrays_type]["arrays"].values() for x in sample["test"]
    ]:
        list_of_lists_of_sets.append([])
        for array in arrays_list:
            list_of_lists_of_sets[-1].append({get_dict_hash(params_dict) for params_dict in array["params"]})

    for initial_array in sample["train"][0][arrays_type]["arrays"].values():
        if len(initial_array["params"]) > 1:
            for j, params_dict1 in enumerate(initial_array["params"][::-1][:-1]):
                hash1 = get_dict_hash(params_dict1)
                delete = True
                for params_dict1 in initial_array["params"][::-1][j + 1 :]:
                    hash2 = get_dict_hash(params_dict1)
                    for lists_of_sets in list_of_lists_of_sets:
                        found = False
                        for hash_set in lists_of_sets:
                            if hash1 in hash_set and hash2 in hash_set:
                                found = True
                                break
                        if not found:
                            delete = False
                            break
                    if delete:
                        delete_blocks.append(hash1)
                        break

    for arrays_list in [x[arrays_type]["arrays"].values() for x in sample["train"]] + [
        x[arrays_type]["arrays"].values() for x in sample["test"]
    ]:
        for array in arrays_list:
            params_list = array["params"]
            j = 0
            while j < len(params_list):
                if get_dict_hash(params_list[j]) in delete_blocks:
                    del params_list[j]
                else:
                    j += 1
    return


def extract_target_blocks(sample, color_params=None):
    target_blocks_cache = []
    params = ["initial", "block_with_side_colors", "min_max_blocks", "max_area_covered", "cut_parts"]
    for n in range(len(sample["train"])):
        target_image = np.uint8(sample["train"][n]["output"])
        target_blocks_cache.append(get_color_scheme(target_image, params=color_params))
        target_blocks_cache[-1].update(generate_blocks(target_image, target_blocks_cache[-1], params=params))
    final_arrays = list(
        set.intersection(
            *[set(target_blocks_cache[n]["blocks"]["arrays"].keys()) for n in range(len(target_blocks_cache))]
        )
    )
    for i, key in enumerate(final_arrays):
        for n in range(len(sample["train"])):
            params_list = [[{"type": "target", "k": i}]]
            add_block(
                sample["train"][n]["blocks"], target_blocks_cache[0]["blocks"]["arrays"][key]["array"], params_list
            )
        for n in range(len(sample["test"])):
            params_list = [[{"type": "target", "k": i}]]
            add_block(sample["test"][n]["blocks"], target_blocks_cache[0]["blocks"]["arrays"][key]["array"], params_list)


def preprocess_sample(sample, params=None, color_params=None, process_whole_ds=False):
    """ make the whole preprocessing for particular sample"""

    for n, image in enumerate(sample["train"]):
        original_image = np.uint8(image["input"])
        target_image = np.uint8(sample["train"][n]["output"])
        sample["train"][n].update(get_color_scheme(original_image, target_image=target_image, params=color_params))
    for n, image in enumerate(sample["test"]):
        original_image = np.uint8(image["input"])
        sample["test"][n].update(get_color_scheme(original_image, params=color_params))

    filter_colors(sample)

    for n, image in enumerate(sample["train"]):
        original_image = np.uint8(image["input"])
        target_image = np.uint8(sample["train"][n]["output"])
        sample["train"][n].update(
            generate_blocks(original_image, sample["train"][n], target_image=target_image, params=params)
        )
    for n, image in enumerate(sample["test"]):
        original_image = np.uint8(image["input"])
        sample["test"][n].update(generate_blocks(original_image, sample["test"][n], params=params))

    if "target" in params:
        extract_target_blocks(sample, color_params)
    filter_blocks(sample)

    for n, image in enumerate(sample["train"]):
        original_image = np.uint8(image["input"])
        target_image = np.uint8(sample["train"][n]["output"])
        sample["train"][n].update(
            generate_masks(original_image, sample["train"][n], target_image=target_image, params=params)
        )
    for n, image in enumerate(sample["test"]):
        original_image = np.uint8(image["input"])
        sample["test"][n].update(generate_masks(original_image, sample["test"][n], params=params))

    return sample
