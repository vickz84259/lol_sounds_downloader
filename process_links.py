import asyncio
import os
import os.path
import json
import hashlib
import time
from concurrent.futures import ThreadPoolExecutor

DIR_PATH = './champions.json/'


def get_file_names():
    return os.listdir(DIR_PATH)


def get_token():
    time_bytes = bytearray(int(time.time()))
    return hashlib.md5(time_bytes).hexdigest()


def get_links(data, file_name):
    print(f'processing {file_name}')
    base_url = 'http://163.172.95.179/VOL/download.php?'
    base_url = f'{base_url}installation_id={get_token()}&champion={file_name}'

    result = []
    for language in data['languages']:
        region_url = f'{base_url}&language={language}'

        for category in data['categories']:
            for voice in category['voices']:
                audio_file_name = voice['file']
                result.append(f'{region_url}&filename={audio_file_name}\n')

    return result


def process_file(file_name):
    path = os.path.join(DIR_PATH, file_name)
    with open(path, 'r') as file:
        data = json.load(file)

    base_file_name = os.path.splitext(file_name)[0]
    return get_links(data, base_file_name)


async def main():
    loop = asyncio.get_running_loop()

    futures = []
    with ThreadPoolExecutor(max_workers=5) as executor:

        for file_name in get_file_names():
            extension = os.path.splitext(file_name)[1]
            if extension == '.json' and 'announcer' in file_name:
                futures.append(
                    loop.run_in_executor(executor, process_file, file_name))

    results = await asyncio.gather(*futures)

    with open('result', 'w') as file:
        for lines in results:
            file.writelines(lines)


if __name__ == "__main__":
    asyncio.run(main())
