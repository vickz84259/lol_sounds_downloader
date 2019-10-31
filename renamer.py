import os
import os.path


def main():
    dir_path = './champions.json/'
    for file_name in os.listdir(dir_path):
        old_word = os.path.join(dir_path, file_name)

        new_word = '_'.join(word.capitalize() for word in file_name.split('_'))
        new_word = os.path.join(dir_path, new_word)

        os.rename(old_word, new_word)


if __name__ == "__main__":
    main()
