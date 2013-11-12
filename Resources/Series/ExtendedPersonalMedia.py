import re, os, os.path
import Media, VideoFiles, Stack, Utils

# Look for episodes.
def Scan(path, files, mediaList, subdirs, language=None, root=None):

    # Scan for video files.
    VideoFiles.Scan(path, files, mediaList, subdirs, root)
    
    # Take top two as show/season, but require at least the top one.
    paths = Utils.SplitPath(path)

    for idx, file in enumerate(files):
        Log('Scan :: file: %s', file)
    
		sport = os.path.basename(os.path.dirname(file))
		print sport
		match = re.search('^(.*?)\.(.*)\.[a-zA-Z0-9]+', os.path.basename(file), re.IGNORECASE)
		if match:
			league = match.group(1)
			print league
			show = sport + '-..-' + league
		else:
			show = sport
		print show
		if match:
			name = match.group(2)
		else:
			name = os.path.basename(file)
		print name
		vid = Media.Episode(show, 1, (idx+1), name, None)
		datematch = re.search('([12][90][0-9][0-9])[\.\/-]([01]?[0-9])[\.\/-]([0-3]?[0-9])', name, re.IGNORECASE)
		if datematch:
			vid.released_at = '%d-%02d-%02d' % (int(datematch.group(1)), int(datematch.group(2)), int(datematch.group(3)))
		vid.parts.append(file)
		mediaList.append(vid)
		print mediaList

