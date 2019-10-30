import asyncio
import os
import os.path
import json
import random
import string
import time

DIR_PATH = './champions.json/'
ALPHANUMERIC = string.ascii_lowercase + string.digits


async def get_file_names(queue):
    for file_name in os.listdir(DIR_PATH):
        extension = os.path.splitext(file_name)[1]
        if extension == '.json' and 'announcer' in file_name:
            await queue.put(file_name)


async def worker(files_queue):
    loop = asyncio.get_running_loop()

    while True:
        try:
            file_name = await files_queue.get()
            await loop.run_in_executor(None, process_file, file_name)
            files_queue.task_done()
        except asyncio.CancelledError:
            break


def get_token():
    return ''.join(random.choice(ALPHANUMERIC) for i in range(32))


def get_links(data, file_name):
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
    start = time.time()

    files_queue = asyncio.Queue()

    producer = asyncio.create_task(get_file_names(files_queue))
    consumers = [asyncio.create_task(worker(files_queue)) for _ in range(2)]

    # Wait for producer to finish
    await producer

    # wait for remaining files to be processed
    await files_queue.join()

    # cancel workers
    for consumer in consumers:
        consumer.cancel()

    print("Process took: {} seconds".format(time.time() - start))


if __name__ == "__main__":
    asyncio.run(main())
