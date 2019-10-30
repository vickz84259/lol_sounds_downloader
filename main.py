import asyncio
import os
import os.path
import json
import random
import string
import time

import aiohttp

DIR_PATH = './champions.json/'
ALPHANUMERIC = string.ascii_lowercase + string.digits


def get_file_names():
    for file_name in os.listdir(DIR_PATH):
        extension = os.path.splitext(file_name)[1]
        if extension == '.json' and 'announcer' in file_name:
            yield file_name


async def url_producer(download_queue):
    loop = asyncio.get_running_loop()

    for file_name in get_file_names():
        file_data = await loop.run_in_executor(None, process_file, file_name)

        for data in file_data:
            await download_queue.put(data)


def get_token():
    return ''.join(random.choice(ALPHANUMERIC) for i in range(32))


def get_links(data, file_name):
    base_url = 'http://163.172.95.179/VOL/download.php?'
    base_url = f'{base_url}installation_id={get_token()}&champion={file_name}'

    for language in data['languages']:
        region_url = f'{base_url}&language={language}'

        for category in data['categories']:
            for voice in category['voices']:
                audio_file_name = voice['file']
                final_url = f'{region_url}&filename={audio_file_name}'

                result = {'url': final_url, 'announcer': file_name}
                result['locale'] = language
                result['name'] = audio_file_name
                yield result


def process_file(file_name):
    path = os.path.join(DIR_PATH, file_name)
    with open(path, 'r') as file:
        data = json.load(file)

    base_file_name = os.path.splitext(file_name)[0]
    return get_links(data, base_file_name)


async def downloader(download_queue, session):
    loop = asyncio.get_running_loop()

    while True:
        try:
            link_data = await download_queue.get()

            url = link_data['url']
            async with session.get(url) as res:
                if res.status == 200 and res.content_type == 'audio/mp3':
                    audio_bytes = await res.read()
                    await loop.run_in_executor(
                        None, save_file, link_data, audio_bytes)
                else:
                    print(f'error: {url}', ' ')
                    print(f'type: {res.content_type}', ' ')
                    print(f'status: {res.status}')

            download_queue.task_done()
        except asyncio.CancelledError:
            break


def save_file(file_data, audio_bytes):
    file_name = f"{file_data['announcer']}_{file_data['locale']}"
    file_name = f"{file_name}_{file_data['name']}.mp3"

    with open(file_name, 'wb') as file:
        file.write(audio_bytes)


async def main():
    start = time.time()

    download_queue = asyncio.Queue()

    producer = asyncio.create_task(url_producer(download_queue))

    max_downloaders = 10
    async with aiohttp.ClientSession() as session:
        tasks = []
        for _ in range(max_downloaders):
            task = asyncio.create_task(downloader(download_queue, session))
            tasks.append(task)

        # Wait for producer to finish
        await producer

        # wait for all files to be downloaded
        await download_queue.join()

        for task in tasks:
            task.cancel()

    print("Process took: {:.2f} seconds".format(time.time() - start))


if __name__ == "__main__":
    asyncio.run(main())
