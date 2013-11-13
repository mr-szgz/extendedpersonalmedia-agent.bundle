import re, os, os.path
import Media, VideoFiles, Stack, Utils
import test

# Look for episodes.
def Scan(path, files, mediaList, subdirs, language=None, root=None):

    # Scan for video files.
    VideoFiles.Scan(path, files, mediaList, subdirs, root)
    
    # Take top two as show/season, but require at least the top one.
    paths = Utils.SplitPath(path)

    for idx, file in enumerate(files):
        Log('Scan :: file: %s', file)
    
        seasonName = os.path.basename(os.path.dirname(file))
        Log('Scan :: season name %s', seasonName)

        name = os.path.basename(file)
        Log('Scan :: show name %s', name)

        vid = Media.Episode(seasonName, 1, (idx+1), name, None)
        datematch = re.search('([12][90][0-9][0-9])[\.\/-]([01]?[0-9])[\.\/-]([0-3]?[0-9])', name, re.IGNORECASE)
        if datematch:
            vid.released_at = '%d-%02d-%02d' % (int(datematch.group(1)), int(datematch.group(2)), int(datematch.group(3)))
        vid.parts.append(file)
        mediaList.append(vid)
        print mediaList

