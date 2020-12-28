import itertools
from enum import Enum, auto
from typing import List

letter_points = {"a": 1, "b": 3, "c": 3, "d": 2, "e": 1, "f": 4, "g": 2, "h": 4, "i": 1, "j": 8, "k": 5, "l": 1, "m": 3,
                 "n": 1, "o": 1, "p": 3, "q": 10, "r": 1, "s": 1, "t": 1, "u": 1, "v": 4, "w": 4, "x": 8, "y": 4,
                 "z": 10}


def load_dictionary():
    dictionary = dict()
    with open("sowpods.txt") as f:
        words = f.readlines()
    for word in words:
        word = word.strip()
        chars = "".join(sorted(list(word)))
        dictionary.setdefault(chars, list()).append(word)
    return dictionary


dictionary = load_dictionary()


def is_word(dictionary, word):
    sorted_letters = "".join(sorted(word))
    words = dictionary.get(sorted_letters, [])
    return word in words


def load_board():
    with open("test_board.txt", encoding='utf-8') as f:
        board = [list(line.strip()) for line in f.readlines()]
    return board[0:15]


def suggest_words(letters, fixed_letters):
    suggestions = set()
    blank_count = sum([1 for letter in letters if letter == "*"])
    non_blank_letters = "".join([letter for letter in letters if letter != "*"])
    find_word_with_blank(non_blank_letters, blank_count, fixed_letters, suggestions)
    return suggestions


def find_word(letters, fixed_letters, playable):
    spaces_in_line = len([square for square in fixed_letters if not square.isalpha()])
    max_letters_to_play = min(len(letters), spaces_in_line)

    for play_letter_count in range(max_letters_to_play, 0, -1):

        # Find which fixed letters to include in our word
        blank_spaces_to_fill = play_letter_count
        fixed_letters_to_include = dict()
        pos = 0
        while blank_spaces_to_fill >= 0 and pos < len(fixed_letters):
            square = fixed_letters[pos]
            contains_letter = square.isalpha()
            if contains_letter:
                fixed_letters_to_include[pos] = square.lower()
            else:
                blank_spaces_to_fill -= 1
            pos += 1

        for p in itertools.combinations(letters, play_letter_count):
            selected_letters = list(p)
            selected_letters.extend(fixed_letters_to_include.values())
            sorted_letters = "".join(sorted(selected_letters))
            words = list(dictionary.get(sorted_letters, []))
            for word in list(words):
                for pos, fixed_letter in fixed_letters_to_include.items():
                    if word[pos] != fixed_letter:
                        words.remove(word)
                        break
            if words:
                playable.update(words)


all_letters = [chr(letter) for letter in range(ord("a"), ord("z") + 1)]


def find_word_with_blank(letters, blank_count, fixed_letters, playable):
    for blanks in itertools.combinations_with_replacement(all_letters, blank_count):
        comb = list(letters)
        comb.extend(list(blanks))
        find_word(comb, fixed_letters, playable)


class Direction(Enum):
    ACROSS = auto()
    DOWN = auto()


def get_squares_in_line(board, coords, direction):
    result = []
    if direction == Direction.ACROSS:
        step = (1, 0)
    else:
        step = (0, 1)
    while coords[0] < 15 and coords[1] < 15:
        row = board[coords[1]]
        square = row[coords[0]]
        result.append(square)
        coords = (coords[0] + step[0], coords[1] + step[1])
    return result


def get_score(board, word, start_coords, direction, tiles_in_hand: List[str]):
    touching_other_word = False

    new_tiles_in_hand = list(tiles_in_hand)

    if direction == Direction.ACROSS:
        step = (1, 0)
    else:
        step = (0, 1)

    coords = start_coords
    word_score = 0
    played_letter_count = 0
    total_crossing_word_score = 0
    played_tiles = {}
    word_multiplier = 1
    for i in range(0, len(word)):
        row = board[coords[1]]
        square = row[coords[0]]
        letter_multiplier = 1

        if not square.isalpha():

            touching_other_word = touching_other_word or is_touching(board, coords)
            played_letter_count += 1

            if square == '£':
                word_multiplier *= 3
            elif square == '^':
                word_multiplier *= 2
            elif square == '+':
                letter_multiplier *= 2
            elif square == '*':
                letter_multiplier *= 3

            required_letter = word[i]
            if required_letter in new_tiles_in_hand:
                played_letter = word[i]
                played_tiles[coords] = played_letter
                word_score += letter_points[required_letter] * letter_multiplier
                new_tiles_in_hand.remove(required_letter)
            else:
                played_letter = word[i].upper()
                played_tiles[coords] = played_letter
                new_tiles_in_hand.remove('*')

            # Check immediately above/below (or to the side) to see if there's another word there
            if has_crossing_word(board, coords, direction):
                crossing_word, crossing_word_score = get_crossing_word_score(board, coords, played_letter, direction)
                if len(crossing_word) > 1:
                    if not is_word(dictionary, crossing_word):
                        return None
                    total_crossing_word_score += crossing_word_score

        elif square.islower():
            word_score += letter_points[square]

        coords = (coords[0] + step[0], coords[1] + step[1])

    if not touching_other_word:
        return None

    word_score *= word_multiplier
    if played_letter_count == 7:
        word_score += 50  # Bingo!

    return word_score + total_crossing_word_score, played_tiles, new_tiles_in_hand


def get_best_move(board, letters):
    suggested_scores = list()
    for y in range(0, 15):
        for x in range(0, 15):
            coords = (x, y)
            for direction in [Direction.ACROSS, Direction.DOWN]:

                # If not the start of a word, don't bother
                if direction == Direction.ACROSS:
                    prev_x, prev_y = x - 1, y
                    if prev_x >= 0 and board[prev_y][prev_x].isalpha():
                        continue
                else:
                    prev_x, prev_y = x, y - 1
                    if prev_y >= 0 and board[prev_y][prev_x].isalpha():
                        continue

                squares = get_squares_in_line(board, coords, direction)

                suggestions = suggest_words(letters, squares)
                for word in suggestions:
                    score = get_score(board, word, coords, direction, letters)
                    if score:
                        suggested_scores.append((word, score[0], score[1], score[2]))

    suggested_scores.sort(key=lambda pair: pair[1], reverse=True)
    return suggested_scores


def is_touching(board, coords):
    x, y = coords
    if x > 0 and board[y][x - 1].isalpha():
        return True
    if x < 14 and board[y][x + 1].isalpha():
        return True
    if y > 0 and board[y - 1][x].isalpha():
        return True
    if y < 14 and board[y + 1][x].isalpha():
        return True
    if coords == (7, 7):
        return True
    return False


def has_crossing_word(board, coords, original_direction):
    x, y = coords
    if original_direction == Direction.DOWN and x > 0 and board[y][x - 1].isalpha():
        return True
    if original_direction == Direction.DOWN and x < 14 and board[y][x + 1].isalpha():
        return True
    if original_direction == Direction.ACROSS and y > 0 and board[y - 1][x].isalpha():
        return True
    if original_direction == Direction.ACROSS and y < 14 and board[y + 1][x].isalpha():
        return True
    return False


def get_crossing_word_score(board, play_coords, play_letter, original_direction):
    result_score = 0
    letter_multiplier = 1
    word_multiplier = 1

    square = board[play_coords[1]][play_coords[0]]
    if square == '£':
        word_multiplier *= 3
    elif square == '^':
        word_multiplier *= 2
    elif square == '+':
        letter_multiplier *= 2
    elif square == '*':
        letter_multiplier *= 3

    result_score += letter_points.get(play_letter, 0) * letter_multiplier
    result_word = [play_letter]

    if original_direction == Direction.ACROSS:
        step = (0, 1)
    else:
        step = (1, 0)

    prev_coords = play_coords
    while True:
        prev_coords = (prev_coords[0] - step[0], prev_coords[1] - step[1])
        if prev_coords[0] < 0 or prev_coords[1] < 0:
            break
        prev_letter = board[prev_coords[1]][prev_coords[0]]
        if not prev_letter.isalpha():
            break
        result_word.insert(0, prev_letter)
        result_score += letter_points.get(prev_letter, 0)

    next_coords = play_coords
    while True:
        next_coords = (next_coords[0] + step[0], next_coords[1] + step[1])
        if next_coords[0] > 14 or next_coords[1] > 14:
            break
        next_letter = board[next_coords[1]][next_coords[0]]
        if not next_letter.isalpha():
            break
        result_word.append(next_letter)
        result_score += letter_points.get(next_letter, 0)

    return "".join(result_word), result_score * word_multiplier


board = load_board()
letters = list("i")
scores = get_best_move(board, letters)
for score in scores:
    print(score)
