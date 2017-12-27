import markdown
from lxml import html
from optparse import OptionParser
import requests
import urlparse
import urllib
import os.path
import shutil
import hashlib
import logging

block_size = 1000 * 1000 # 1MB
MARKDOWN_LINK = 'https://raw.githubusercontent.com/decrypto-org/blockchain-papers/master/README.md'



def validate_file(file_path, hash):
    m = hashlib.md5()
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(1000 * 1000) # 1MB
            if not chunk:
                break
            m.update(chunk)
    return m.hexdigest() == hash



def download_with_resume(url, file_path, hash=None, timeout=10):
    """
    url: remote file url
    file_path: save as file name
    hash: provide if hash is available
    """

    # check if file is present/already downloaded locally
    if os.path.exists(file_path):
    	print "File %s already downloaded" % url
        return
    # Temporary file names have .part
    tmp_file_path = file_path + '.part'
    

    first_byte = os.path.getsize(tmp_file_path) if os.path.exists(tmp_file_path) else 0
    file_mode = 'ab' if first_byte else 'wb'
    file_size = -1
    
    # check if file exists remotely
    if requests.head(url).status_code == 404:
        print "File %s not found" % url
        return

    # check if html page
    try:
        if "text/html" in requests.head(url).headers["content-type"] or "text/html" in requests.head(url).headers["Content-Type"]:
    	   print "Downloading html page at %s" % url
    	   urllib.urlretrieve(url, url.split('/')[-1])
    	   return       
    except KeyError: # continue if content-type is not found
        print "content-type not found: %s" % url
        pass

    #get remote file size
    try:
        file_size = int(requests.head(url).headers['Content-length'])
    except KeyError:
        # if can't, download the file without resuming
        urllib.urlretrieve(url, url.split('/')[-1])
        return 

    # resume if file is present
    if first_byte > 0:    
    	print 'Resuming download of file \'%s\' at %.1fMB' % (url, first_byte / 1e6)
        print "File size: %s" % file_size
        print "Downloaded file size: %s" % os.path.getsize(tmp_file_path)
    else:
    #start a new download
    	print 'Starting download of file \'%s\' at %.1fMB' % (url, first_byte / 1e6)

    logging.debug('Starting download at %.1fMB' % (first_byte / 1e6))
    
    print 'File size is %s' % file_size
    logging.debug('File size is %s' % file_size)
    headers = {"Range": "bytes=%s-" % first_byte}
    r = requests.get(url, headers=headers, stream=True)
    print "Saving as: %s" % tmp_file_path
    with open(tmp_file_path, file_mode) as f:
        for chunk in r.iter_content(chunk_size=block_size):
            if chunk: # filter out keep-alive new chunks
                f.write(chunk)

    # redownload the file
    if os.path.getsize(tmp_file_path) > file_size:
        redownload(url, {"Range": "bytes=0-"}, tmp_file_path, 'wb')

    # if size of remote and local file are same, rename
    if file_size == os.path.getsize(tmp_file_path):
        # if there's a hash value, validate the file
        if hash and not validate_file(tmp_file_path, hash):
            raise Exception('Error validating the file against its MD5 hash')
        print "File downloaded! Renaming file to: %s" % file_path
        shutil.move(tmp_file_path, file_path)
    elif file_size != os.path.getsize(tmp_file_path):
        print "Download error: falling back to unresumable download"
        urllib.urlretrieve(url, url.split('/')[-1])
    elif file_size == -1:
        raise Exception('Error getting Content-Length from server: %s' % url)

       # rename the temp download file to the correct name if fully downloaded
        

def parse_markdown(body):
	#Generate HTML from Markdown
	doc = html.fromstring(markdown.markdown(body))
	#Generate links
	for link in doc.xpath('//a'):
		#Check if valid links with a scheme, location and path
		result = urlparse.urlparse(link.get('href'))
		if all([result.scheme, result.netloc, result.path]):
			download_from_url(link.text, link.get('href'))

def download_from_url(name, link):
	if name == None:
		download_with_resume(link, str(link))
	else:
		download_with_resume(link, (name+".pdf"))

def redownload(url, headers, tmp_file_path, file_mode):
        print "Deleting file: %s" % tmp_file_path
        os.remove(tmp_file_path)
        r = requests.get(url, headers=headers, stream=True)
        print "Saving as: %s" % tmp_file_path
        with open(tmp_file_path, file_mode) as f:
            for chunk in r.iter_content(chunk_size=block_size):
                if chunk: # filter out keep-alive new chunks
                    f.write(chunk)

def download_markdown_file(link):
    "Downloading %s and saving to: %s" % (link, link.split('/')[-1])
    urllib.urlretrieve(link, link.split('/')[-1])
    r = requests.get(link)
    body = r.content
    body_unicode = body.decode('utf-8')
    return body_unicode


def start():
	parser = OptionParser()
	parser.add_option("-u", "--url", dest="markdown_link", help="Markdown file to download and extract links from")
	(options, args) = parser.parse_args()
    	if options.markdown_link:
		body = download_markdown_file(options.markdown_link)
		parse_markdown(body)
	else:
		print "Provide a markdown url using -u or --url as a command line parameter"

if __name__ == '__main__':
	start()
