import asyncio
import os
import os.path
import json
import random
import string
import time

import aiohttp

import gcp
import utils

DIR_PATH = './champions.json/'
ALPHANUMERIC = string.ascii_lowercase + string.digits

CONFIG = utils.get_config()
bucket_name = CONFIG['bucket_name']
# Base url for uploads
BASE_URL = f'https://www.googleapis.com/upload/storage/v1/b/{bucket_name}/o'


def get_file_names():
    for file_name in os.listdir(DIR_PATH):
        extension = os.path.splitext(file_name)[1]
        if extension == '.json' and 'announcer' in file_name:
            yield file_name


async def url_producer(download_queue):
    loop = asyncio.get_running_loop()

    for file_name in get_file_names():
        result = await loop.run_in_executor(None, process_file, file_name)

        for data in result:
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


async def downloader(download_queue, upload_queue, session):
    while True:
        try:
            file_data = await download_queue.get()

            url = file_data['url']
            async with session.get(url) as res:
                if res.status == 200 and res.content_type == 'audio/mp3':
                    audio_bytes = await res.read()
                    file_data['bytes'] = audio_bytes

                    await upload_queue.put(file_data)
                else:
                    print(f'error: {url}', ' ')
                    print(f'type: {res.content_type}', ' ')
                    print(f'status: {res.status}')

            download_queue.task_done()
        except asyncio.CancelledError:
            break


async def uploader(upload_queue, session):
    while True:
        try:
            file_data = await upload_queue.get()

            file_name = f"{file_data['announcer']}/{file_data['locale']}"
            file_name = f"{file_name}/{file_data['name']}.mp3"

            url = f'{BASE_URL}?uploadType=media&name={file_name}'
            data = file_data['bytes']

            async with session.post(url, data=data) as res:
                if res.status != 200:
                    print(f'error: {file_name}', ' ')
                    print(f'status: {res.status}')

            upload_queue.task_done()
        except asyncio.CancelledError:
            break


async def main():
    start = time.time()

    download_queue = asyncio.Queue()
    upload_queue = asyncio.Queue()

    upload_headers = {'Content-Type': 'audio/mp3'}
    token_dict = gcp.get_token()
    upload_headers['Authorization'] = f"Bearer {token_dict['access_token']}"

    async with aiohttp.ClientSession() as download_session, \
            aiohttp.ClientSession(headers=upload_headers) as upload_session:

        producer = asyncio.create_task(url_producer(download_queue))

        downloaders = []
        max_workers = 20
        for _ in range(max_workers):
            task = asyncio.create_task(
                downloader(download_queue, upload_queue, download_session))
            downloaders.append(task)

        uploaders = []
        for _ in range(max_workers):
            task = asyncio.create_task(uploader(upload_queue, upload_session))
            uploaders.append(task)

        # Wait for producer to finish
        await producer

        # wait for all files to be downloaded
        await download_queue.join()

        # wait for all files to be uploaded
        await upload_queue.join()

        # Cancel pending tasks since both downloads and uploads are complete
        for task in downloaders + uploaders:
            task.cancel()

    print("Process took: {:.2f} seconds".format(time.time() - start))


if __name__ == "__main__":
    asyncio.run(main())
