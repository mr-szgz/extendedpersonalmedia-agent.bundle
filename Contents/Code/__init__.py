# Version Date: 2017-08-22

import datetime, os, sys, time, re, locale, ConfigParser
from string import Template

# Series agent name
SERIES_AGENT_NAME = 'Extended Personal Media Shows'

def logDebug(methodName, message, *args):
    if bool(Prefs['logger.debug.enabled']):
        Log(methodName + ' :: ' + message, *args)

def log(methodName, message, *args):
    Log(methodName + ' :: ' + message, *args)

def isBlank (string):
    '''
    Tests whether the string is blank
    '''
    return not(string and string.strip())

def isNotBlank (string):
    '''
    Tests whether the string is not blank
    '''
    return bool(string and string.strip())

# Only use unicode if it's supported, which it is on Windows and OS X,
# but not Linux. This allows things to work with non-ASCII characters
# without having to go through a bunch of work to ensure the Linux
# filesystem is UTF-8 "clean".
#
def unicodize(s):
    filename = s

    logDebug('unicodize', 'before unicodizing: %s', str(filename))
    if os.path.supports_unicode_filenames:
        try: filename = unicode(s.decode('utf-8'))
        except: pass
    logDebug('unicodize', 'after unicodizing: %s', str(filename))
    return filename

def findFile(filePaths, fileNames):
    '''
    Find one of the specified file names in the list starting at the lowest directory passed in and
    walking up the directory tree until the root directory is found or one of the files in the list is found
    '''
    for filePath in filePaths:
        rootDirFound = False
        parentDir = filePath

        # Get the parent directory for the file
        if os.path.isfile(filePath):
            parentDir = os.path.dirname(parentDir)

        # iterate over the directory
        while not rootDirFound:
            logDebug('findFile', 'looking in parent directory %s', parentDir)
            # create the file path
            for fileName in fileNames:
                pathToFind = os.path.normpath(os.path.normcase(os.path.join(parentDir, fileName)))
                logDebug('findFile', 'determining whether file %s exists', pathToFind)
                if os.path.exists(pathToFind) and os.path.isfile(pathToFind):
                    logDebug('findFile', 'file %s exists', pathToFind)
                    return pathToFind
                else:
                    logDebug('findFile', 'file %s does not exist', pathToFind)

            # go up a directory
            logDebug('findFile', 'going up a directory')
            newDir = os.path.abspath(os.path.dirname( parentDir ))

            logDebug('findFile', 'new directory path %s', newDir)
            # if the new directory and parent directory are the same then we have reached the top directory - stop looking for the file
            if newDir == parentDir:
                logDebug('findFile', 'root directory %s found - stopping directory traversal', newDir)
                rootDirFound = True
            else:
                parentDir = newDir

    return None

def isSubdir(path, directory):
    '''
    Returns true if *path* in a subdirectory of *directory*.
    '''
    if len(path) > len(directory):
        sep = os.path.sep.encode('ascii') if isinstance(directory, bytes) else os.path.sep
        dirComp = directory.rstrip(sep) + sep
        logDebug('isSubdir','comparing [%s] to [%s]', path, dirComp)
        if path.startswith(dirComp):
            logDebug('isSubdir', 'path is a subdirectory')
            return True
    return False

def loadTextFromFile(filePath):
    '''
    Load the text text from the specified file
    '''
    textUnicode = None
    # If the file exists read in its contents
    if os.path.exists(filePath) is True:
        text = None
        logDebug('loadTextFromFile', 'file exists - reading contents')
        try:
            # Read the text from the file
            text = Core.storage.load(filePath, False)
        except Exception as e:
            logDebug('loadTextFromFile', 'error occurred reading contents of file %s : %s', filePath, e)

        # try to decode the contents
        try:
            # decode using the system default
            logDebug('loadTextFromFile', 'decoding string using utf-8 - not ignoring errors')
            textUnicode = unicode(text, 'utf-8')
        except Exception as e:
            logDebug('loadTextFromFile', 'could not decode contents of summary file %s : %s', filePath, e)
            # decode using utf-8 and ignore errors
            logDebug('loadTextFromFile', 'decoding string using utf-8 - ignoring errors')
            textUnicode = unicode(text, 'utf-8', errors='ignore')

    return textUnicode

def getSummaryFileExtension():
    '''
    Gets the summary file extension to use from the plugin preferences
    '''
    fileExt = Prefs['summary.file.extension']
    if isBlank(fileExt):
        fileExt = 'summary'
    logDebug('getSummaryFileExtension', 'using summary file extension %s', fileExt)
    fileExt = '.'+fileExt
    return fileExt

def getMetadataFileExtension():
    '''
    Gets the metadata file extension to use from the plugin preferences
    '''
    fileExt = Prefs['metadata.file.extension']
    if isBlank(fileExt):
        fileExt = 'metadata'
    logDebug('getMetadataFileExtension', 'using metadata file extension %s', fileExt)
    fileExt = '.'+fileExt
    return fileExt
    
def findSeasonSummary(filePaths, fileNames):
    seasonSummary = None
    logDebug('findSeasonSummary', 'looking for files with names %s in path list %s', str(fileNames), str(filePaths))
    filePath = findFile(filePaths, fileNames)
    if filePath != None:
        log('findSeasonSummary', 'found season summary file %s', filePath)
        seasonSummary = loadTextFromFile(filePath)
    else:
        log('findSeasonSummary', 'season summary file not found')

    return seasonSummary

def findShowSummary(filePaths, fileNames):
    showSummary = None
    logDebug('findShowSummary', 'looking for files with names %s in path list %s', str(fileNames), str(filePaths))
    filePath = findFile(filePaths, fileNames)
    if filePath != None:
        log('findShowSummary', 'found show summary file %s', filePath)
        showSummary = loadTextFromFile(filePath)
    else:
        log('findShowSummary', 'show summary file not found')

    return showSummary

def findShowMetadata(filePaths, fileNames):
    filePath = None
    logDebug('findShowMetadata', 'looking for files with names %s in path list %s', str(fileNames), str(filePaths))
    filePath = findFile(filePaths, fileNames)
    if filePath != None:
        log('findShowMetadata', 'found show metadata file %s', filePath)
    else:
        log('findShowMetadata', 'show metadata file not found')

    return filePath


class BaseMediaParser(object):
    '''
        Parses the file name and determines the type of tile that was found
    '''

    fileNameRegex = r'^(?P<fileWithoutExt>.*)\..+$'

    # Episode name REGEX
    partRegexes = [
                    r'(?P<episodeTitle>.+)(\.[ ]*|-[ ]*)(part[0-9]+|pt[0-9]+)',
                    r'(?P<episodeTitle>.+)([ ]+)(part[0-9]+|pt[0-9]+)'
                    ]

    def __init__(self):
        self.showSummary = None
        self.seasonSummary = None
        self.episodeTitle = None
        self.episodeSummary = None
        self.episodeReleaseDate = None

    def stripPart(self, episodeTitle):
        processed = episodeTitle
        # Test whether it contains part
        for partRegex in self.partRegexes:
            match = re.search(partRegex, processed)
            if match:
                logDebug('stripPart', 'episode title %s contains part', processed)
                processed = match.group('episodeTitle').strip()
                logDebug('stripPart', 'stripped episode title: %s', processed)
                break

        return processed
       
    def scrub(self, string, charsToRemove):
        processed = string
        stringAsList = list(charsToRemove)
        i = 0
        while i + 3 <= len(stringAsList):
            processed = re.sub(re.escape(stringAsList[i]), stringAsList[i+2], processed)
            i = i + 4
        if i < len(stringAsList):
            logDebug('scrubString', 'did not process the remaining characters [%s] in the string - verify the scrub string is formatted correctly i.e. A=B,C=D', charsToRemove[i:len(charsToRemove)])
        logDebug('scrubString', 'original: [%s] scrubbed: [%s]', string, processed)
        return processed

    def setValues(self, match):
        # set the episode title
        self.episodeTitle = self.stripPart(match.group('episodeTitle').strip())
        # check to see if title should be scrubbed
        if bool(Prefs['episode.title.scrub.enabled']):
            episodeScrubChars = Prefs['episode.title.scrub.characters']
            if isNotBlank(episodeScrubChars):
                logDebug('setValues', 'scrubbing enabled - using scrub characters [%s] ', episodeScrubChars)
                self.episodeTitle = self.scrub(self.episodeTitle, episodeScrubChars)
            else:
                logDebug('setValues', 'scrubbing enabled - scrub characters are blank [%s] - skipping scrubbing', episodeScrubChars)
        
        # set the episode release date
        # if episodeMonth and episodeDay is present in the regex then the episode release date is in the file name and will be used
        if 'episodeMonth' in match.groupdict() and 'episodeDay' in match.groupdict():
            logDebug('setValues', 'episodeMonth found in the regular expression - extracting release date from the file name')
            self.seasonNumber = None
            if 'seasonNumber' in match.groupdict():
                self.seasonNumber = int(match.group('seasonNumber').strip())
            self.episodeYear = None
            if 'episodeYear' in match.groupdict():
                self.episodeYear = int(match.group('episodeYear').strip())
            # if the regex did not contain a year use the season number
            if self.episodeYear is None and self.seasonNumber is not None and self.seasonNumber >= 1000:
                self.episodeYear = self.seasonNumber
            self.episodeMonth = int(match.group('episodeMonth').strip())
            self.episodeDay = int(match.group('episodeDay').strip())
            # Create the date
            logDebug('setValues', 'year %s month %s day %s', self.episodeYear, self.episodeMonth, self.episodeDay)
            self.episodeReleaseDate = datetime.datetime(self.episodeYear, self.episodeMonth, self.episodeDay)
            logDebug('setValues', 'episode date: %s', str(self.episodeReleaseDate))

        # set the episode summary
        # get the summary file path
        # find out what file format is being used
        match = re.search(self.fileNameRegex, self.mediaFile)
        if match:
            fileWithoutExt = match.group('fileWithoutExt').strip()
            logDebug('setValues', 'file name without extension %s', fileWithoutExt)
            summaryFilePath = fileWithoutExt + getSummaryFileExtension()
            logDebug('setValues', 'looking for summary file %s', summaryFilePath)
            # If the summary file exist read in the contents
            if os.path.exists(summaryFilePath) is True:
                logDebug('setValues', 'episode summary file %s exists', summaryFilePath)
                self.episodeSummary = loadTextFromFile(summaryFilePath)
            else:
                logDebug('setValues', 'episode summary file does not exist')
            
    def getSupportedRegexes(self):
        return []

    def containsMatch(self, mediaFile):
        retVal = False
        # Iterate over the list of regular expressions
        for regex in self.getSupportedRegexes():
            # Find out what file format is being used
            match = re.search(regex, mediaFile, re.IGNORECASE)
            if match:
                retVal = True
                break

        return retVal


    def parse(self, mediaFile):
        self.mediaFile = mediaFile

        # Iterate over the list of regular expressions
        for regex in self.getSupportedRegexes():
            # Find out what file format is being used
            match = re.search(regex, mediaFile, re.IGNORECASE)
            logDebug('parse', 'regex %s - matches: %s', regex, match)
            if match:
                logDebug('parse', 'found matches')
                self.setValues(match)
                break

    def getEpisodeTitle(self):
        return self.episodeTitle

    def getEpisodeSummary(self):
        return self.episodeSummary

    def getEpisodeReleaseDate(self):
        return self.episodeReleaseDate
        

class SeriesDateBasedMediaParser(BaseMediaParser):

    def getSupportedRegexes(self):
        return [
                # \Show Title - 2012-09-19_23 - Episode Title.mp4
                # \Show.Title.2012.09.19_23.Episode.Title.mp4
                r'[\\/](?P<showTitle>[^\\/]+?)[ ]*[-\.]{0,1}[ ]*(?P<episodeYear>[0-9]{4})[-\. ](?P<episodeMonth>[0-9]{2})[-\. ](?P<episodeDay>[0-9]{2})(_(?P<episodeIndex>[0-9]+)){0,2}[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$',
                # \Show Title - 09-19-2012_23 - Episode Title.mp4
                # \Show.Title.09.19.2012_23.Episode.Title.mp4
                r'[\\/](?P<showTitle>[^\\/]+?)[ ]*[-\.]{0,1}[ ]*(?P<episodeMonth>[0-9]{2})[-\. ](?P<episodeDay>[0-9]{2})[-\. ](?P<episodeYear>[0-9]{4})(_(?P<episodeIndex>[0-9]+)){0,2}[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$',
                #Show Title\2012 - Season Title\Show Title - 2012-09-19 - Episode Title.mp4
                #Show Title\2012 - Season Title\2012-09-19 - Episode Title.mp4
                #Show Title\2012\Show Title - 2012-09-19 - Episode Title.mp4
                #Show Title\2012\2012-09-19 - Episode Title.mp4
                r'(?P<showTitle>[^\\/]+)[\\/](?P<seasonNumber>[0-9]{4})([-\. ]+(?P<seasonTitle>[^\\/]+)){0,1}[\\/][^\\/]*?(?P<episodeYear>[0-9]{4})[-\. ](?P<episodeMonth>[0-9]{2})[-\. ](?P<episodeDay>[0-9]{2})(_(?P<episodeIndex>[0-9]+)){0,2}[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$' ,
                #2012 - Season Title\Show Title\Show Title - 2012-09-19 - Episode Title.mp4
                #2012 - Season Title\Show Title\2012-09-19 - Episode Title.mp4
                #2012\Show Title\Show Title - 2012-09-19 - Episode Title.mp4
                #2012\Show Title\2012-09-19 - Episode Title.mp4
                r'(?P<seasonNumber>[0-9]{4})([-\. ]+(?P<seasonTitle>[^\\/]+)){0,1}[\\/](?P<showTitle>[^\\/]+)[\\/][^\\/]*?(?P<episodeYear>[0-9]{4})[-\. ](?P<episodeMonth>[0-9]{2})[-\. ](?P<episodeDay>[0-9]{2})(_(?P<episodeIndex>[0-9]+)){0,2}[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$' ,
                #Show Title\2012 - Season Title\Show Title - 09-19-2013 - Episode Title.mp4
                #Show Title\2012 - Season Title\09-19-2013 - Episode Title.mp4
                #Show Title\2012\Show Title - 09-19-2013 - Episode Title.mp4
                #Show Title\2012\09-19-2013 - Episode Title.mp4
                r'(?P<showTitle>[^\\/]+)[\\/](?P<seasonNumber>[0-9]{4})([-\. ]+(?P<seasonTitle>[^\\/]+)){0,1}[\\/][^\\/]*?(?P<episodeMonth>[0-9]{2})[-\. ](?P<episodeDay>[0-9]{2})[-\. ](?P<episodeYear>[0-9]{4})(_(?P<episodeIndex>[0-9]+)){0,2}[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$' ,
                #2012 - Season Title\Show Title\Show Title - 09-19-2013 - Episode Title.mp4
                #2012 - Season Title\Show Title\09-19-2013 - Episode Title.mp4
                #2012\Show Title\Show Title - 09-19-2013 - Episode Title.mp4
                #2012\Show Title\09-19-2013 - Episode Title.mp4
                r'(?P<seasonNumber>[0-9]{4})([-\. ]+(?P<seasonTitle>[^\\/]+)){0,1}[\\/](?P<showTitle>[^\\/]+)[\\/][^\\/]*?(?P<episodeMonth>[0-9]{2})[-\. ](?P<episodeDay>[0-9]{2})[-\. ](?P<episodeYear>[0-9]{4})(_(?P<episodeIndex>[0-9]+)){0,2}[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$' ,
                #Show Title\2012\Show Title - 09-19 - Episode Title.mp4
                #Show Title\2012\09-19 - Episode Title.mp4
                r'(?P<showTitle>[^\\/]+)[\\/](?P<seasonNumber>[0-9]{4})([-\. ]+(?P<seasonTitle>[^\\/]+)){0,1}[\\/][^\\/]*?(?P<episodeMonth>[0-9]{2})[-\. ](?P<episodeDay>[0-9]{2})(_(?P<episodeIndex>[0-9]+)){0,2}[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$',
                #2012\Show Title\Show Title - 09-19 - Episode Title.mp4
                #2012\Show Title\09-19 - Episode Title.mp4
                r'(?P<seasonNumber>[0-9]{4})([-\. ]+(?P<seasonTitle>[^\\/]+)){0,1}[\\/](?P<showTitle>[^\\/]+)[\\/][^\\/]*?(?P<episodeMonth>[0-9]{2})[-\. ](?P<episodeDay>[0-9]{2})(_(?P<episodeIndex>[0-9]+)){0,2}[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$'
                ]
                 
class SeriesEpisodeMediaParser(BaseMediaParser):

    def getSupportedRegexes(self):
        return [
                #\Show Title - s2012e09 - Episode Title.mp4
                r'[\\/](?P<showTitle>[^\\/]+?)[ ]*[-\.]{0,1}[ ]*[sc](?P<seasonNumber>[0-9]+)[e](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$',
                #Show Title\01 - Season Title\Show Title - s2012e09 - Episode Title.mp4
                #Show Title\01\Show Title - s2012e09 - Episode Title.mp4
                r'(?P<showTitle>[^\\/]+)[\\/][sc|season|chapter|lesson]*?[ ]*?(?P<seasonNumber>[0-9]+)([-\. ]+(?P<seasonTitle>[^\\/]+)){0,1}[\\/][^\\/]*?[e](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$',
                #01 - Season Title\Show Title\Show Title - s2012e09 - Episode Title.mp4
                #01\Show Title\Show Title - s2012e09 - Episode Title.mp4
                r'[sc|season|chapter|lesson]*?[ ]*?(?P<seasonNumber>[0-9]+)([-\. ]+(?P<seasonTitle>[^\\/]+)){0,1}[\\/](?P<showTitle>[^\\/]+)[\\/][^\\/]*?[e](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$',
                #Show Title\01 - Season Title\09 - Episode Title.mp4
                #Show Title\01\09 - Episode Title.mp4
                #Training Title\Lesson1\05 - Title.mp4
                r'(?P<showTitle>[^\\/]+)[\\/][sc|season|chapter|lesson]*?[ ]*?(?P<seasonNumber>[0-9]+)([-\. ]+(?P<seasonTitle>[^\\/]+)){0,1}[\\/](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$',
                #01 - Season Title\Show Title\09 - Episode Title.mp4
                #01\Show Title\09 - Episode Title.mp4
                r'[sc|season|chapter|lesson]*?[ ]*?(?P<seasonNumber>[0-9]+)([-\. ]+(?P<seasonTitle>[^\\/]+)){0,1}[\\/](?P<showTitle>[^\\/]+)[\\/](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$',
                #Show Title\2012\Show Title - s2012e09 - Episode Title.mp4
                #Show Title\2012\e09 - Episode Title.mp4
                r'(?P<showTitle>[^\\/]+)[\\/][sc|season|chapter|lesson]*?[ ]*?(?P<seasonNumber>[0-9]+)[\\/][^\\/]*?[e](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$',
                #2012\Show Title\Show Title - s2012e09 - Episode Title.mp4
                #2012\Show Title\e09 - Episode Title.mp4
                r'[sc|season|chapter|lesson]*?[ ]*?(?P<seasonNumber>[0-9]+)[\\/](?P<showTitle>[^\\/]+)[\\/][^\\/]*?[e](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$',
                #Show Title\2012\09 - Episode Title.mp4
                r'(?P<showTitle>[^\\/]+)[\\/][sc|season|chapter|lesson]*?[ ]*?(?P<seasonNumber>[0-9]+)[\\/](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$',
                #2012\Show Title\09 - Episode Title.mp4
                r'[sc|season|chapter|lesson]*?[ ]*?(?P<seasonNumber>[0-9]+)[\\/](?P<showTitle>[^\\/]+)[\\/](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$'
                ]

    def setValues(self, match):
        # set the common values
        BaseMediaParser.setValues(self, match)
        
        # else check to see if the "use last modified timestamp" preference is enabled
        if bool(Prefs['use.last.modified.timestamp.enabled']):
            logDebug('setValues', "Use last modified timestamp option is enabled - extracting release date from the file's last modified timestamp")
            # Get the release date from the file
            lastModifiedTimestamp = os.path.getmtime(self.mediaFile)
            self.episodeReleaseDate = datetime.date.fromtimestamp(lastModifiedTimestamp)
            logDebug('setValues', 'episode date: %s', str(self.episodeReleaseDate))
        

class SeriesDatedEpisodeMediaParser(BaseMediaParser):

    def getSupportedRegexes(self):
        return [
            #\Show Title - s2012e09 - 2015-12-31 - Episode Title.mp4
            r'[\\/](?P<showTitle>[^\\/]+?)[ ]*[-\.]{0,1}[ ]*[sc](?P<seasonNumber>[0-9]+)[e](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeYear>[0-9]{4})[-\. ](?P<episodeMonth>[0-9]{2})[-\. ](?P<episodeDay>[0-9]{2})[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$',
            #\Show Title - s2012e09 - 12-31-2015 - Episode Title.mp4
            r'[\\/](?P<showTitle>[^\\/]+?)[ ]*[-\.]{0,1}[ ]*[sc](?P<seasonNumber>[0-9]+)[e](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeMonth>[0-9]{2})[-\. ](?P<episodeDay>[0-9]{2})[-\. ](?P<episodeYear>[0-9]{4})[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$',
            #Show Title\s2012e09 - 2015-12-31 - Episode Title.mp4
            r'(?P<showTitle>[^\\/]+)[\\/][sc](?P<seasonNumber>[0-9]+)[e](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeYear>[0-9]{4})[-\. ](?P<episodeMonth>[0-9]{2})[-\. ](?P<episodeDay>[0-9]{2})[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$',
            #Show Title\s2012e09 - 12-31-2015 - Episode Title.mp4
            r'(?P<showTitle>[^\\/]+)[\\/][sc](?P<seasonNumber>[0-9]+)[e](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeMonth>[0-9]{2})[-\. ](?P<episodeDay>[0-9]{2})[-\. ](?P<episodeYear>[0-9]{4})[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$',
            #Show Title\s2015\e09 - 2015-12-31 - Episode Title.mp4
            r'(?P<showTitle>[^\\/]+)[\\/][sc|season|chapter|lesson]*?[ ]*?(?P<seasonNumber>[0-9]+)[\\/][e](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeYear>[0-9]{4})[-\. ](?P<episodeMonth>[0-9]{2})[-\. ](?P<episodeDay>[0-9]{2})[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$',
            #Show Title\s2015\e09 - 12-31-2015 - Episode Title.mp4
            r'(?P<showTitle>[^\\/]+)[\\/][sc|season|chapter|lesson]*?[ ]*?(?P<seasonNumber>[0-9]+)[\\/][e](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeMonth>[0-9]{2})[-\. ](?P<episodeDay>[0-9]{2})[-\. ](?P<episodeYear>[0-9]{4})[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$',
            #Show Title\e09 - 2015-12-31 - Episode Title.mp4
            r'(?P<showTitle>[^\\/]+)[\\/][e](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeYear>[0-9]{4})[-\. ](?P<episodeMonth>[0-9]{2})[-\. ](?P<episodeDay>[0-9]{2})[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$',
            #Show Title\e09 - 12-31-2015 - Episode Title.mp4
            r'(?P<showTitle>[^\\/]+)[\\/][e](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeMonth>[0-9]{2})[-\. ](?P<episodeDay>[0-9]{2})[-\. ](?P<episodeYear>[0-9]{4})[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$',
            #Show Title - e09 - 2015-12-31 - Episode Title.mp4
            r'[\\/](?P<showTitle>[^\\/]+?)[ ]*[-\.]{0,1}[ ]*[e](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeYear>[0-9]{4})[-\. ](?P<episodeMonth>[0-9]{2})[-\. ](?P<episodeDay>[0-9]{2})[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$',
            #Show Title - e09 - 12-31-2015 - Episode Title.mp4
            r'[\\/](?P<showTitle>[^\\/]+?)[ ]*[-\.]{0,1}[ ]*[e](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeMonth>[0-9]{2})[-\. ](?P<episodeDay>[0-9]{2})[-\. ](?P<episodeYear>[0-9]{4})[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$'
        ]
        
def Start():
    log('Start', 'starting agents %s, %s', SERIES_AGENT_NAME)
    pass

class CustomParserMetadata(object):
    '''
        Gets the metadata from the specified file
    '''
                        
    def __init__(self, filePath):
        self.filePath = filePath
        self.metadata = ConfigParser.SafeConfigParser()
        self.metadata.read(filePath)
                                                                
    def release(self):
        return self.metadata.get('metadata', 'release')

    def studio(self):
        return self.metadata.get('metadata', 'studio')

    def genres(self):
        return self.metadata.get('metadata', 'genres')


class ExtendedPersonalMediaAgentTVShows(Agent.TV_Shows):
    name = SERIES_AGENT_NAME
    languages = Locale.Language.All()
    accepts_from = ['com.plexapp.agents.localmedia']

    def search(self, results, media, lang):
        logDebug('search', 'media id: %s', media.id)
        logDebug('search', 'media file name: %s', str(media.filename))
        logDebug('search', 'media primary metadata: %s', str(media.primary_metadata))
        logDebug('search', 'media primary agent: %s', str(media.primary_agent))
        logDebug('search', 'media title: %s', str(media.title))
        logDebug('search', 'media show: %s', str(media.show))
        logDebug('search', 'media name: %s', str(media.name))
        logDebug('search', 'media season: %s', str(media.season))
        logDebug('search', 'media episode: %s', str(media.episode))

        # Compute the GUID based on the media hash.
        try:
            part = media.items[0].parts[0]
            # Get the modification time to use as the year.
            filename = unicodize(part.file)
            log('search', 'part file name: %s', filename)
        except:
            log('search', 'part does not exist')

        results.Append(MetadataSearchResult(id=media.id, name=media.show, year=None, lang=lang, score=100))

    def update(self, metadata, media, lang):
        #test.test('Extended Personal Media - Scan')
        logDebug('update', 'meta data agent object id: %s', id(self))
        logDebug('update', 'metadata: %s', str(metadata))
        logDebug('update', 'media: %s', str(media))
        logDebug('update', 'lang: %s', str(lang))
        # set the metadata title
        metadata.title = media.title
        # list of series parsers
        series_parsers = [SeriesDatedEpisodeMediaParser(), SeriesDateBasedMediaParser(), SeriesEpisodeMediaParser()]
        showTitle = metadata.title
        # list of file paths
        showFilePaths = []
        for s in media.seasons:
            logDebug('update', 'season %s', s)
            seasonMetadata = metadata.seasons[s]
            logDebug('update', 'season metadata %s', seasonMetadata)
            metadata.seasons[s].index = int(s)
            seasonFilePaths = []

            for e in media.seasons[s].episodes:
                logDebug('update', 'episode: %s', e)
                # Make sure metadata exists, and find sidecar media.
                episodeMetadata = metadata.seasons[s].episodes[e]
                logDebug('update', 'episode metadata: %s', episodeMetadata)
                episodeMedia = media.seasons[s].episodes[e].items[0]

                file = episodeMedia.parts[0].file
                logDebug('update', 'episode file path: %s', file)
                absFilePath = os.path.abspath(unicodize(file))
                log('update', 'absolute file path: %s', absFilePath)

                # Iterate over the list of parsers and parse the file path
                for parser in series_parsers:
                    if parser.containsMatch(absFilePath) is True:
                        logDebug('update', 'parser object id: %s', id(parser))
                        log('update', 'parser %s contains match - parsing file path', parser)
                        parser.parse(absFilePath)

                        # set the episode data
                        episodeMetadata.title = parser.getEpisodeTitle()
                        episodeMetadata.summary = parser.getEpisodeSummary()
                        episodeMetadata.originally_available_at = parser.getEpisodeReleaseDate()
                        log('update', 'episode.title: %s', episodeMetadata.title)
                        log('update', 'episode.summary: %s', episodeMetadata.summary)
                        log('update', 'episode.originally_available_at: %s', episodeMetadata.originally_available_at)

                        # add the file path to the season file path list
                        seasonFilePaths = self.addFilePath(seasonFilePaths, absFilePath)
                        # add the file path to the show file path list
                        showFilePaths = self.addFilePath(showFilePaths, absFilePath)

                        break

            # Check for season summary
            summaryFileExt = getSummaryFileExtension()
            # Build the list of the file names that we should look for
            seasonFileNames = [showTitle + '-S' + s + summaryFileExt, showTitle + '-s' + s + summaryFileExt, 
                                showTitle + '-C' + s + summaryFileExt, showTitle + '-c' + s + summaryFileExt, 
                                showTitle + '-L' + s + summaryFileExt, showTitle + '-l' + s + summaryFileExt, 
                                'season-' + s + summaryFileExt, 
                                'chapter-' + s + summaryFileExt, 
                                'lesson-' + s + summaryFileExt, 
                                'S' + s + summaryFileExt, 's' + s + summaryFileExt, 
                                'C' + s + summaryFileExt, 'c' + s + summaryFileExt, 
                                'L' + s + summaryFileExt, 'l' + s + summaryFileExt]
            seasonSummary = findSeasonSummary(seasonFilePaths, seasonFileNames)
            if seasonSummary != None:
                seasonMetadata.summary = seasonSummary
                log('update', 'season.summary: %s', seasonMetadata.summary)


        # Check for show summary
        summaryFileExt = getSummaryFileExtension()
        showSummary = findShowSummary(showFilePaths, [showTitle + summaryFileExt, 'show' + summaryFileExt])
        if showSummary != None:
            metadata.summary = showSummary
            log('update', 'show.summary: %s', metadata.summary)

        if bool(Prefs['use.show.metadata.enabled']):
            logDebug('update', 'use metadata file option is enabled - extracting metadata from metadata file')
            metadataFileExt = getMetadataFileExtension()
            showMetadataFilePath = findShowMetadata(showFilePaths, [showTitle + metadataFileExt, 'show' + metadataFileExt])
            if showMetadataFilePath != None:
                fileMetadata = CustomParserMetadata(showMetadataFilePath)
                release = fileMetadata.release()
                if release is not None:
                    metadata.originally_available_at = datetime.datetime.strptime(release, '%Y-%m-%d')
                    log('update', 'show.metadata - release: %s', release)
                studio = fileMetadata.studio()
                if studio is not None:
                    metadata.studio = studio
                    log('update', 'show.metadata - studio: %s', studio)
                genres = fileMetadata.genres() 
                if genres is not None:
                    metadata.genres = genres.split(",")
                    log('update', 'show.metadata - genres: %s', genres)


    def addFilePath(self, filePaths, newFilePath):
        '''
        Adds the specified file path to the list if it is a sub-directory or a unique file path
        '''
        evalPaths = []

        newDirPath = newFilePath
        if os.path.isfile(newDirPath):
            newDirPath = os.path.dirname(newDirPath)
        # determine if the new path is a sub-path or a new path
        logDebug('addFilePath', 'verifying file path [%s] should be added', newDirPath)
        appendPath = True
        for path in filePaths:
            path = os.path.normpath(os.path.normcase(path))
            logDebug('addFilePath', 'existing path [%s]', path)
            newDirPath = os.path.normpath(os.path.normcase(newDirPath))
            logDebug('addFilePath', 'new path [%s]', newDirPath)
            if newDirPath == path:
                logDebug('addFilePath', 'paths are equivalent - keeping existing path [%s]', path)
                evalPaths.append(path)
                appendPath = False
            elif newDirPath.startswith(path):
                logDebug('addFilePath', 'path [%s] is a subdirectory of [%s] - keeping new path [%s]', newDirPath, path, newDirPath)
                evalPaths.append(newDirPath)
                appendPath = False
            else:
                logDebug('addFilePath', 'keeping existing path [%s]', newDirPath)
                evalPaths.append(path)

        # path is a new path - keep it
        if appendPath:
            logDebug('addFilePath', 'keeping new path [%s]', newDirPath)
            evalPaths.append(newDirPath)

        return evalPaths
