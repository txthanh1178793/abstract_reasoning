import numpy as np
from src.preprocessing import get_color, get_color_scheme, get_dict_hash
from src.functions import (
    filter_list_of_dicts,
    combine_two_lists,
    intersect_two_lists,
    swap_two_colors,
)
import random
from src.preprocessing import find_grid, get_predict, get_mask_from_block_params
import itertools


class predictor:
    def __init__(self, params=None, preprocess_params=None):
        self.params = params
        self.preprocess_params = preprocess_params
        self.solution_candidates = []
        if self.params is not None and "rrr_input" in params:
            self.rrr_input = params["rrr_input"]
        else:
            self.rrr_input = True

    def retrive_params_values(self, params, color_scheme):
        new_params = {}
        for k, v in params.items():
            if k[-5:] == "color":
                new_params[k] = get_color(v, color_scheme["colors"])
                if new_params[k] < 0:
                    return 1, None
            else:
                new_params[k] = v
        return 0, new_params

    def reflect_rotate_roll(self, image, inverse=False):
        if self.params is not None and "reflect" in self.params:
            reflect = self.params["reflect"]
        else:
            reflect = (False, False)
        if self.params is not None and "rotate" in self.params:
            rotate = self.params["rotate"]
        else:
            rotate = 0
        if self.params is not None and "roll" in self.params:
            roll = self.params["roll"]
        else:
            roll = (0, 0)

        result = image.copy()

        if inverse:
            if reflect[0]:
                result = result[::-1]
            if reflect[1]:
                result = result[:, ::-1]
            result = np.rot90(result, -rotate)
            result = np.roll(result, -roll[1], axis=1)
            result = np.roll(result, -roll[0], axis=0)
        else:
            result = np.roll(result, roll[0], axis=0)
            result = np.roll(result, roll[1], axis=1)
            result = np.rot90(result, rotate)
            if reflect[1]:
                result = result[:, ::-1]
            if reflect[0]:
                result = result[::-1]

        return result

    def get_images(self, k, train=True):
        if train:
            if self.rrr_input:
                original_image = self.reflect_rotate_roll(
                    np.uint8(self.sample["train"][k]["input"])
                )
            else:
                original_image = np.uint8(self.sample["train"][k]["input"])
            target_image = self.reflect_rotate_roll(
                np.uint8(self.sample["train"][k]["output"])
            )
            return original_image, target_image
        else:
            if self.rrr_input:
                original_image = self.reflect_rotate_roll(
                    np.uint8(self.sample["test"][k]["input"])
                )
            else:
                original_image = np.uint8(self.sample["test"][k]["input"])
            return original_image

    def process_prediction(self, image):
        return self.reflect_rotate_roll(image, inverse=True)

    def predict_output(self, image, params):
        """ predicts 1 output image given input image and prediction params"""
        return 1, None

    def filter_colors(self):
        for i in range(10):
            list_of_colors = [
                get_dict_hash(color_dict)
                for color_dict in self.sample["train"][0]["colors"][i]
            ]
            for color_scheme in self.sample["train"][1:]:
                new_set = set(
                    [
                        get_dict_hash(color_dict)
                        for color_dict in color_scheme["colors"][i]
                    ]
                )
                list_of_colors = [x for x in list_of_colors if x in new_set]
                if len(list_of_colors) == 0:
                    break
            if len(list_of_colors) > 1:
                colors_to_delete = list_of_colors[1:]

                for color_scheme in self.sample["train"]:
                    for color_dict in color_scheme["colors"][i].copy():
                        if get_dict_hash(color_dict) in colors_to_delete:
                            color_scheme["colors"][i].remove(color_dict)
        return

    def init_call(self):
        self.filter_colors()

    def process_one_sample(self, k, initial=False):
        """ processes k train sample and updates self.solution_candidates"""
        local_candidates = []
        original_image, target_image = self.get_images(k)
        return 0

    def process_full_train(self):
        for k in range(len(self.sample["train"])):
            status = self.process_one_sample(k, initial=(k == 0))
            if status != 0:
                return 1

        if len(self.solution_candidates) == 0:
            return 2

        return 0

    def add_candidates_list(self, image, target_image, colors, params):
        status, prediction = self.predict_output(image, params)
        if (
            status != 0
            or prediction.shape != target_image.shape
            or not (prediction == target_image).all()
        ):
            return []

        result = [params.copy()]
        for k, v in params.copy().items():
            if k[-5:] == "color":
                temp_result = result.copy()
                result = []
                for dict in temp_result:
                    for color_dict in colors[v]:
                        temp_dict = dict.copy()
                        temp_dict[k] = color_dict
                        result.append(temp_dict)

        return result

    def update_solution_candidates(self, local_candidates, initial):
        if initial:
            self.solution_candidates = local_candidates
        else:
            self.solution_candidates = filter_list_of_dicts(
                local_candidates, self.solution_candidates
            )
        if len(self.solution_candidates) == 0:
            return 4
        else:
            return 0

    def __call__(self, sample):
        """ works like fit_predict"""
        self.sample = sample
        self.init_call()
        self.initial_train = list(sample["train"]).copy()

        if self.params is not None and "skip_train" in self.params:
            skip_train = min(len(sample["train"]) - 2, self.params["skip_train"])
            train_len = len(self.initial_train) - skip_train
        else:
            train_len = len(self.initial_train)

        answers = []
        for _ in self.sample["test"]:
            answers.append([])
        result_generated = False

        all_subsets = list(itertools.combinations(self.initial_train, train_len))
        for subset in all_subsets:
            self.sample["train"] = subset
            status = self.process_full_train()
            if status != 0:
                continue

            for test_n, test_data in enumerate(self.sample["test"]):
                original_image = self.get_images(test_n, train=False)
                color_scheme = self.sample["test"][test_n]
                for params_dict in self.solution_candidates:
                    status, params = self.retrive_params_values(
                        params_dict, color_scheme
                    )
                    if status != 0:
                        continue
                    params["block_cache"] = self.sample["test"][test_n]["blocks"]
                    params["mask_cache"] = self.sample["test"][test_n]["masks"]
                    params["color_scheme"] = self.sample["test"][test_n]
                    status, prediction = self.predict_output(original_image, params)
                    if status != 0:
                        continue

                    answers[test_n].append(self.process_prediction(prediction))
                    result_generated = True

        if result_generated:
            return 0, answers
        else:
            return 3, None


class fill(predictor):
    """inner fills all pixels around all pixels with particular color with new color
    outer fills the pixels with fill color if all neighbour colors have background color"""

    def __init__(self, params=None, preprocess_params=None):
        super().__init__(params, preprocess_params)
        self.type = params["type"]  # inner or outer
        if "pattern" in params:
            self.pattern = params["pattern"]
        else:
            self.pattern = [[True, True, True], [True, False, True], [True, True, True]]

    def predict_output(self, image, params):
        """ predicts 1 output image given input image and prediction params"""
        result = image.copy()
        image_with_borders = np.ones((image.shape[0] + 2, image.shape[1] + 2)) * 11
        image_with_borders[1:-1, 1:-1] = image
        for i in range(1, image_with_borders.shape[0] - 1):
            for j in range(1, image_with_borders.shape[1] - 1):
                if self.type == "outer":
                    if image[i - 1, j - 1] == params["fill_color"]:
                        image_with_borders[i - 1 : i + 2, j - 1 : j + 2][
                            np.array(self.pattern)
                        ] = params["background_color"]
                elif self.type == "inner":
                    if (
                        image_with_borders[i - 1 : i + 2, j - 1 : j + 2][
                            np.array(self.pattern)
                        ]
                        == params["background_color"]
                    ).all():
                        result[i - 1, j - 1] = params["fill_color"]
                elif self.type == "inner_ignore_background":
                    if (
                        image_with_borders[i - 1 : i + 2, j - 1 : j + 2][
                            np.array(self.pattern)
                        ]
                        != params["background_color"]
                    ).all():
                        result[i - 1, j - 1] = params["fill_color"]
                elif self.type == "isolated":
                    if not (
                        image_with_borders[i - 1 : i + 2, j - 1 : j + 2][
                            np.array(self.pattern)
                        ]
                        == params["background_color"]
                    ).any():
                        result[i - 1, j - 1] = params["fill_color"]
                elif self.type == "full":
                    if (
                        i - 1 + self.pattern.shape[0] > image.shape[0]
                        or j - 1 + self.pattern.shape[1] > image.shape[1]
                    ):
                        continue
                    if (
                        image[
                            i - 1 : i - 1 + self.pattern.shape[0],
                            j - 1 : j - 1 + self.pattern.shape[1],
                        ][np.array(self.pattern)]
                        == params["background_color"]
                    ).all():
                        result[
                            i - 1 : i - 1 + self.pattern.shape[0],
                            j - 1 : j - 1 + self.pattern.shape[1],
                        ][np.array(self.pattern)] = params["fill_color"]

                else:
                    return 6, None
        if self.type == "outer":
            result = image_with_borders[1:-1, 1:-1]
        return 0, result

    def process_one_sample(self, k, initial=False):
        """ processes k train sample and updates self.solution_candidates"""
        local_candidates = []
        original_image, target_image = self.get_images(k)
        if original_image.shape != target_image.shape:
            return 5, None
        for background_color in range(10):
            if not (target_image == background_color).any():
                continue
            for fill_color in range(10):
                if not (target_image == fill_color).any():
                    continue
                mask = np.logical_and(
                    target_image != background_color, target_image != fill_color
                )
                if not (target_image == original_image)[mask].all():
                    continue
                params = {
                    "background_color": background_color,
                    "fill_color": fill_color,
                }

                local_candidates = local_candidates + self.add_candidates_list(
                    original_image,
                    target_image,
                    self.sample["train"][k]["colors"],
                    params,
                )
        return self.update_solution_candidates(local_candidates, initial)


class puzzle(predictor):
    """inner fills all pixels around all pixels with particular color with new color
    outer fills the pixels with fill color if all neighbour colors have background color"""

    def __init__(self, params=None, preprocess_params=None):
        super().__init__(params, preprocess_params)
        self.intersection = params["intersection"]

    def initiate_factors(self, target_image):
        t_n, t_m = target_image.shape
        factors = []
        grid_color_list = []
        if self.intersection < 0:
            grid_color, grid_size = find_grid(target_image)
            if grid_color < 0:
                return factors, []
            factors = [grid_size]
            grid_color_list = self.sample["train"][0]["colors"][grid_color]
        else:
            for i in range(1, t_n + 1):
                for j in range(1, t_m + 1):
                    if (t_n - self.intersection) % i == 0 and (
                        t_m - self.intersection
                    ) % j == 0:
                        factors.append([i, j])
        return factors, grid_color_list

    def retrive_params_values(self, params, color_scheme):
        pass

    def predict_output(self, image, color_scheme, factor, params, block_cache):
        """ predicts 1 output image given input image and prediction params"""
        skip = False
        for i in range(factor[0]):
            for j in range(factor[1]):
                status, array = get_predict(
                    image, params[i][j][0], block_cache, color_scheme
                )
                if status != 0:
                    skip = True
                    break
                n, m = array.shape

                if i == 0 and j == 0:
                    predict = np.uint8(
                        np.zeros(
                            (
                                (n - self.intersection) * factor[0] + self.intersection,
                                (m - self.intersection) * factor[1] + self.intersection,
                            )
                        )
                    )
                    if self.intersection < 0:
                        predict += get_color(
                            self.grid_color_list[0], color_scheme["colors"]
                        )

                predict[
                    i * (n - self.intersection) : i * (n - self.intersection) + n,
                    j * (m - self.intersection) : j * (m - self.intersection) + m,
                ] = array
            if skip:
                return 1, None

        return 0, predict

    def initiate_candidates_list(self, initial_values=None):
        """creates an empty candidates list corresponding to factors
        for each (m,n) factor it is m x n matrix of lists"""
        candidates = []
        if not initial_values:
            initial_values = []
        for n_factor, factor in enumerate(self.factors):
            candidates.append([])
            for i in range(factor[0]):
                candidates[n_factor].append([])
                for j in range(factor[1]):
                    candidates[n_factor][i].append(initial_values.copy())
        return candidates

    def process_one_sample(self, k, initial=False):
        """ processes k train sample and updates self.solution_candidates"""

        original_image, target_image = self.get_images(k)

        candidates_num = 0
        t_n, t_m = target_image.shape
        color_scheme = self.sample["train"][k]
        new_candidates = self.initiate_candidates_list()
        for n_factor, factor in enumerate(self.factors.copy()):
            for i in range(factor[0]):
                for j in range(factor[1]):
                    if initial:
                        local_candidates = self.sample["train"][k]["blocks"][
                            "arrays"
                        ].keys()
                        # print(local_candidates)
                    else:
                        local_candidates = self.solution_candidates[n_factor][i][j]

                    for data in local_candidates:
                        if initial:
                            # print(data)
                            array = self.sample["train"][k]["blocks"]["arrays"][data][
                                "array"
                            ]
                            params = self.sample["train"][k]["blocks"]["arrays"][data][
                                "params"
                            ]
                        else:
                            params = [data]
                            status, array = get_predict(
                                original_image,
                                data,
                                self.sample["train"][k]["blocks"],
                                color_scheme,
                            )
                            if status != 0:
                                continue

                        n, m = array.shape
                        # work with valid candidates only
                        if n <= 0 or m <= 0:
                            continue
                        if (
                            n - self.intersection
                            != (t_n - self.intersection) / factor[0]
                            or m - self.intersection
                            != (t_m - self.intersection) / factor[1]
                        ):
                            continue

                        start_n = i * (n - self.intersection)
                        start_m = j * (m - self.intersection)

                        if not (
                            (
                                n
                                == target_image[
                                    start_n : start_n + n, start_m : start_m + m
                                ].shape[0]
                            )
                            and (
                                m
                                == target_image[
                                    start_n : start_n + n, start_m : start_m + m
                                ].shape[1]
                            )
                        ):
                            continue

                        # adding the candidate to the candidates list
                        if (
                            array
                            == target_image[
                                start_n : start_n + n, start_m : start_m + m
                            ]
                        ).all():
                            new_candidates[n_factor][i][j].extend(params)
                            candidates_num += 1
                    # if there is no candidates for one of the cells the whole factor is invalid
                    if len(new_candidates[n_factor][i][j]) == 0:
                        self.factors[n_factor] = [0, 0]
                        break
                if self.factors[n_factor][0] == 0:
                    break

        self.solution_candidates = new_candidates

        if candidates_num > 0:
            return 0
        else:
            return 1

    def filter_factors(self, local_factors):
        for factor in self.factors:
            found = False
            for new_factor in local_factors:
                if factor == new_factor:
                    found = True
                    break
            if not found:
                factor = [0, 0]

        return

    def process_full_train(self):

        for k in range(len(self.sample["train"])):
            original_image, target_image = self.get_images(k)
            if k == 0:
                self.factors, self.grid_color_list = self.initiate_factors(target_image)
            else:
                local_factors, grid_color_list = self.initiate_factors(target_image)
                self.filter_factors(local_factors)
                self.grid_color_list = filter_list_of_dicts(
                    grid_color_list, self.grid_color_list
                )

            status = self.process_one_sample(k, initial=(k == 0))
            if status != 0:
                return 1

        if len(self.solution_candidates) == 0:
            return 2

        return 0

    def __call__(self, sample):
        """ works like fit_predict"""
        self.sample = sample
        status = self.process_full_train()
        if status != 0:
            return status, None

        answers = []
        for _ in self.sample["test"]:
            answers.append([])

        result_generated = False
        for test_n, test_data in enumerate(self.sample["test"]):
            original_image = self.get_images(test_n, train=False)
            color_scheme = self.sample["test"][test_n]
            for n_factor, factor in enumerate(self.factors):
                if factor[0] > 0 and factor[1] > 0:
                    status, prediction = self.predict_output(
                        original_image,
                        color_scheme,
                        factor,
                        self.solution_candidates[n_factor],
                        self.sample["test"][test_n]["blocks"],
                    )
                    if status == 0:
                        answers[test_n].append(self.process_prediction(prediction))
                        result_generated = True

        if result_generated:
            return 0, answers
        else:
            return 3, None


class pattern(predictor):
    """applies pattern to every pixel with particular color"""

    def __init__(self, params=None, preprocess_params=None):
        super().__init__(params, preprocess_params)
        # self.type = params["type"]

    def get_patterns(self, original_image, target_image):
        pattern_list = []
        if target_image.shape[0] % original_image.shape[0] != 0:
            self.try_self = False
            return []
        if target_image.shape[1] % original_image.shape[1] != 0:
            self.try_self = False
            return []

        size = [
            target_image.shape[0] // original_image.shape[0],
            target_image.shape[1] // original_image.shape[1],
        ]

        if size[0] != original_image.shape[0] or size[1] != original_image.shape[1]:
            self.try_self = False

        if max(size) == 1:
            return []
        for i in range(original_image.shape[0]):
            for j in range(original_image.shape[1]):
                current_block = target_image[
                    i * size[0] : (i + 1) * size[0], j * size[1] : (j + 1) * size[1]
                ]
                pattern_list = combine_two_lists(pattern_list, [current_block])

        return pattern_list

    def init_call(self):
        self.try_self = True
        for k in range(len(self.sample["train"])):
            original_image, target_image = self.get_images(k)
            patterns = self.get_patterns(original_image, target_image)
            if k == 0:
                self.all_patterns = patterns
            else:
                self.all_patterns = intersect_two_lists(self.all_patterns, patterns)
        if self.try_self:
            self.additional_patterns = ["self", "processed"]
        else:
            self.additional_patterns = []

    def predict_output(self, image, params):
        if params["swap"]:
            status, new_image = swap_two_colors(image)
            if status != 0:
                new_image = image
        else:
            new_image = image
        mask = new_image == params["mask_color"]
        if params["pattern_num"] == "self":
            pattern = image
        elif params["pattern_num"] == "processed":
            pattern = new_image
        else:
            pattern = self.all_patterns[params["pattern_num"]]

        size = (mask.shape[0] * pattern.shape[0], mask.shape[1] * pattern.shape[1])
        result = np.ones(size) * params["background_color"]
        for i in range(mask.shape[0]):
            for j in range(mask.shape[1]):
                if mask[i, j] != params["inverse"]:
                    result[
                        i * pattern.shape[0] : (i + 1) * pattern.shape[0],
                        j * pattern.shape[1] : (j + 1) * pattern.shape[1],
                    ] = pattern

        return 0, result

    def process_one_sample(self, k, initial=False):
        """ processes k train sample and updates self.solution_candidates"""
        local_candidates = []
        original_image, target_image = self.get_images(k)

        if len(self.all_patterns) + len(self.additional_patterns) == 0:
            return 6

        for pattern_num in (
            list(range(len(self.all_patterns))) + self.additional_patterns
        ):
            for mask_color in range(10):
                if not (original_image == mask_color).any():
                    continue
                for background_color in range(10):
                    if not (target_image == background_color).any():
                        continue
                    for inverse in [True, False]:
                        for swap in [True, False]:
                            params = {
                                "pattern_num": pattern_num,
                                "mask_color": mask_color,
                                "background_color": background_color,
                                "inverse": inverse,
                                "swap": swap,
                            }

                            status, predict = self.predict_output(
                                original_image, params
                            )

                            if status == 0 and (predict == target_image).all():
                                local_candidates = (
                                    local_candidates
                                    + self.add_candidates_list(
                                        original_image,
                                        target_image,
                                        self.sample["train"][k]["colors"],
                                        params,
                                    )
                                )

        return self.update_solution_candidates(local_candidates, initial)


class mask_to_block(predictor):
    """applies several masks to block"""

    def __init__(self, params=None, preprocess_params=None):
        super().__init__(params, preprocess_params)
        if params is not None and "mask_num" in params:
            self.mask_num = params["mask_num"]
        else:
            self.mask_num = 1

    def apply_mask(self, image, mask, color):
        if image.shape != mask.shape:
            return 1, None
        result = image.copy()
        result[mask] = color
        return 0, result

    def predict_output(self, image, params):
        status, block = get_predict(
            image,
            params["block"],
            block_cache=params["block_cache"],
            color_scheme=params["color_scheme"],
        )

        if status != 0:
            return status, None
        result = block

        for mask_param, color_param in zip(params["masks"], params["colors"]):
            status, mask = get_mask_from_block_params(
                image,
                mask_param,
                block_cache=params["block_cache"],
                mask_cache=params["mask_cache"],
                color_scheme=params["color_scheme"],
            )
            if status != 0:
                return status, None
            color = get_color(color_param, params["color_scheme"]["colors"])
            if color < 0:
                return 6, None
            status, result = self.apply_mask(result, mask, color)
            if status != 0:
                return status, None

        return 0, result

    def find_mask_color(self, target, mask, ignore_mask):
        visible_mask = np.logical_and(np.logical_not(ignore_mask), mask)
        if not (visible_mask).any():
            return -1
        visible_part = target[visible_mask]
        colors = np.unique(visible_part)
        if len(colors) == 1:
            return colors[0]
        else:
            return -1

    def add_block(self, target_image, ignore_mask, k):
        results = []
        for block_hash, block in self.sample["train"][k]["blocks"]["arrays"].items():
            # print(ignore_mask)
            if (block["array"].shape == target_image.shape) and (
                block["array"][np.logical_not(ignore_mask)]
                == target_image[np.logical_not(ignore_mask)]
            ).all():
                results.append(block_hash)

        if len(results) == 0:
            return 1, None
        else:
            return 0, results

    def generate_result(self, target_image, masks, colors, ignore_mask, k):
        if len(masks) == self.mask_num:
            status, blocks = self.add_block(target_image, ignore_mask, k)
            if status != 0:
                return 8, None
            result = [
                {"block": block, "masks": masks, "colors": colors} for block in blocks
            ]
            return 0, result

        result = []
        for mask_hash, mask in self.sample["train"][k]["masks"]["arrays"].items():
            if mask_hash in masks:
                continue
            if mask["array"].shape != target_image.shape:
                continue
            color = self.find_mask_color(target_image, mask["array"], ignore_mask)
            if color < 0:
                continue
            new_ignore_mask = np.logical_or(mask["array"], ignore_mask)
            status, new_results = self.generate_result(
                target_image, [mask_hash] + masks, [color] + colors, new_ignore_mask, k
            )
            if status != 0:
                continue
            result = result + new_results

        if len(result) < 0:
            return 9, None
        else:
            return 0, result

    def process_one_sample(self, k, initial=False):
        """ processes k train sample and updates self.solution_candidates"""

        candidates = []
        original_image, target_image = self.get_images(k)

        if initial:
            ignore_mask = np.zeros_like(target_image, dtype=bool)
            status, candidates = self.generate_result(
                target_image, [], [], ignore_mask, k
            )
            if status != 0:
                return status
            candidates = [
                {"block": block_params, "masks": x["masks"], "colors": x["colors"]}
                for x in candidates
                for block_params in self.sample["train"][k]["blocks"]["arrays"][
                    x["block"]
                ]["params"]
            ]
            for i in range(self.mask_num):
                candidates = [
                    {
                        "block": x["block"],
                        "masks": [
                            x["masks"][j] if j != i else mask_param
                            for j in range(self.mask_num)
                        ],
                        "colors": [
                            x["colors"][j] if j != i else color_param
                            for j in range(self.mask_num)
                        ],
                    }
                    for x in candidates
                    for mask_param in self.sample["train"][k]["masks"]["arrays"][
                        x["masks"][i]
                    ]["params"]
                    for color_param in self.sample["train"][k]["colors"][x["colors"][i]]
                ]

        else:
            for candidate in self.solution_candidates:
                params = candidate.copy()
                params["block_cache"] = self.sample["train"][k]["blocks"]
                params["mask_cache"] = self.sample["train"][k]["masks"]
                params["color_scheme"] = self.sample["train"][k]

                status, prediction = self.predict_output(original_image, params)
                if status != 0:
                    continue
                if (
                    prediction.shape == target_image.shape
                    and (prediction == target_image).all()
                ):
                    candidates.append(candidate)

        self.solution_candidates = candidates
        if len(self.solution_candidates) == 0:
            return 10

        return 0

    def __call__(self, sample):
        """ works like fit_predict"""
        self.sample = sample
        self.init_call()
        self.initial_train = list(sample["train"]).copy()

        if self.params is not None and "skip_train" in self.params:
            skip_train = min(len(sample["train"]) - 2, self.params["skip_train"])
            train_len = len(self.initial_train) - skip_train
        else:
            train_len = len(self.initial_train)

        answers = []
        for _ in self.sample["test"]:
            answers.append([])
        result_generated = False

        all_subsets = list(itertools.combinations(self.initial_train, train_len))
        for subset in all_subsets:
            self.sample["train"] = subset
            status = self.process_full_train()
            if status != 0:
                return status, None

            random.shuffle(self.solution_candidates)
            self.solution_candidates = self.solution_candidates[:300]
            print(len(self.solution_candidates))
            for test_n, test_data in enumerate(self.sample["test"]):
                original_image = self.get_images(test_n, train=False)
                color_scheme = self.sample["test"][test_n]
                for params_dict in self.solution_candidates:
                    params = params_dict.copy()
                    params["block_cache"] = self.sample["test"][test_n]["blocks"]
                    params["mask_cache"] = self.sample["test"][test_n]["masks"]
                    params["color_scheme"] = color_scheme

                    status, prediction = self.predict_output(original_image, params)
                    if status != 0:
                        continue

                    answers[test_n].append(self.process_prediction(prediction))
                    result_generated = True

        if result_generated:
            return 0, answers
        else:
            return 3, None


class pattern_from_blocks(pattern):
    """applies pattern to every pixel with particular color"""

    def __init__(self, params=None, preprocess_params=None):
        super().__init__(params, preprocess_params)

    def predict_output(self, image, params, pattern=None, mask=None):
        if pattern is None:
            status, pattern = get_predict(
                image,
                params["pattern"],
                block_cache=params["block_cache"],
                color_scheme=params["color_scheme"],
            )
            if status != 0:
                return 1, None
        if mask is None:
            status, mask = get_mask_from_block_params(
                image,
                params["mask"],
                block_cache=params["block_cache"],
                mask_cache=params["mask_cache"],
                color_scheme=params["color_scheme"],
            )
            if status != 0:
                return 2, None

        size = (mask.shape[0] * pattern.shape[0], mask.shape[1] * pattern.shape[1])
        result = np.ones(size) * params["background_color"]
        for i in range(mask.shape[0]):
            for j in range(mask.shape[1]):
                if mask[i, j]:
                    result[
                        i * pattern.shape[0] : (i + 1) * pattern.shape[0],
                        j * pattern.shape[1] : (j + 1) * pattern.shape[1],
                    ] = pattern

        return 0, result

    def process_one_sample(self, k, initial=False):
        """ processes k train sample and updates self.solution_candidates"""
        local_candidates = []
        original_image, target_image = self.get_images(k)

        if initial:
            for _, block in self.sample["train"][k]["blocks"]["arrays"].items():
                pattern = block["array"]
                if (
                    target_image.shape[0] % pattern.shape[0] != 0
                    or target_image.shape[1] % pattern.shape[1] != 0
                ):
                    continue
                for _, mask_path in self.sample["train"][k]["masks"]["arrays"].items():
                    mask = mask_path["array"]
                    if (
                        target_image.shape[0] != pattern.shape[0] * mask.shape[0]
                        or target_image.shape[1] != pattern.shape[1] * mask.shape[1]
                    ):
                        continue
                    for background_color in range(10):
                        if not (target_image == background_color).any():
                            continue
                        params = {"background_color": background_color}

                        status, predict = self.predict_output(
                            original_image, params, pattern=pattern, mask=mask
                        )

                        if status == 0 and (predict == target_image).all():
                            for pattern_params in block["params"]:
                                for mask_params in mask_path["params"]:
                                    for color_dict in self.sample["train"][k]["colors"][
                                        background_color
                                    ]:
                                        params = {
                                            "background_color": color_dict,
                                            "mask": mask_params,
                                            "pattern": pattern_params,
                                        }
                                        local_candidates.append(params)

        else:
            block_cache = self.sample["train"][k]["blocks"]
            mask_cache = self.sample["train"][k]["masks"]
            color_scheme = self.sample["train"][k]

            for candidate in self.solution_candidates:
                status, pattern = get_predict(
                    original_image,
                    candidate["pattern"],
                    block_cache=block_cache,
                    color_scheme=color_scheme,
                )
                if status != 0:
                    continue
                if (
                    target_image.shape[0] % pattern.shape[0] != 0
                    or target_image.shape[1] % pattern.shape[1] != 0
                ):
                    continue

                status, mask = get_mask_from_block_params(
                    original_image,
                    candidate["mask"],
                    block_cache=block_cache,
                    mask_cache=mask_cache,
                    color_scheme=color_scheme,
                )
                if status != 0:
                    continue
                if (
                    target_image.shape[0] != pattern.shape[0] * mask.shape[0]
                    or target_image.shape[1] != pattern.shape[1] * mask.shape[1]
                ):
                    continue
                background_color = get_color(
                    candidate["background_color"], color_scheme["colors"]
                )
                if not (target_image == background_color).any():
                    continue
                params = {"background_color": background_color}

                status, predict = self.predict_output(
                    original_image, params, pattern=pattern, mask=mask
                )

                if status == 0 and (predict == target_image).all():
                    local_candidates.append(candidate)

        return self.update_solution_candidates(local_candidates, initial)


class colors(predictor):
    """returns colors as answers"""

    def __init__(self, params=None, preprocess_params=None):
        super().__init__(params, preprocess_params)
        # self.type = params["type"]

    def predict_output(self, image, params):
        if params["type"] == "one":
            return 0, np.array([[params["color"]]])
        if params["type"] == "mono_vert":
            num = (image == params["color"]).sum()
            if num <= 0:
                return 7, 0
            return 0, np.array([[params["color"]] * num])
        if params["type"] == "mono_hor":
            num = (image == params["color"]).sum()
            if num <= 0:
                return 7, 0
            return 0, np.array([[params["color"] * num]])
        return 9, None

    def process_one_sample(self, k, initial=False):
        """ processes k train sample and updates self.solution_candidates"""
        local_candidates = []
        original_image, target_image = self.get_images(k)

        if target_image.shape[0] == 1 and target_image.shape[1] == 1:
            params = {"type": "one", "color": int(target_image[0, 0])}
            local_candidates = local_candidates + self.add_candidates_list(
                original_image, target_image, self.sample["train"][k]["colors"], params
            )
        if target_image.shape[0] == 1:
            params = {"type": "mono_vert", "color": int(target_image[0, 0])}
            local_candidates = local_candidates + self.add_candidates_list(
                original_image, target_image, self.sample["train"][k]["colors"], params
            )
        if target_image.shape[1] == 1:
            params = {"type": "mono_hor", "color": int(target_image[0, 0])}
            local_candidates = local_candidates + self.add_candidates_list(
                original_image, target_image, self.sample["train"][k]["colors"], params
            )

        # else:
        #     for candidate in self.solution_candidates:
        #         if candidate['type'] == 'one':
        #             if target_image.shape[0] != 1 or target_image.shape[1] != 1:
        #                 continue
        #         local_candidates = local_candidates + self.add_candidates_list(
        #             original_image,
        #             target_image,
        #             self.sample["train"][k]["colors"],
        #             candidate,
        #         )

        return self.update_solution_candidates(local_candidates, initial)


# TODO: fill pattern - more general surface type
# TODO: reconstruct pattern
# TODO: reconstruct pattern
# TODO: colors functions
