# Version Date: 2016-01-02

import datetime, os, sys, time, re, locale, ConfigParser
from string import Template

# Series agent name
SERIES_AGENT_NAME = 'Extended Personal Media Shows'

def logDebug(methodName, message, *args):
    if bool(Prefs['logger.debug.enabled']):
        Log(methodName + ' :: ' + message, *args)
    
def log(methodName, message, *args):
    Log(methodName + ' :: ' + message, *args)

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
    
    def scrub(self, string):
        processed = ''
        matches = re.split(r'[\.\-_]+', string)
        idx = 1
        if matches is not None:
            for match in matches:
                processed = processed + match
                if idx < len(matches):
                    processed = processed + ' '
                idx = idx + 1
        else:
            processed = string
            
        logDebug('scrubString', 'original: [%s] scrubbed: [%s]', string, processed)
        return processed
    
    def setValues(self, mediaFile, match):
        # set the episode title
        self.episodeTitle = self.scrub(self.stripPart(match.group('episodeTitle').strip()))
        
        # set the episode summary
        self.episodeSummary = None
        # Get the summary file path
        # Find out what file format is being used
        match = re.search(self.fileNameRegex, mediaFile)
        if match:
            fileWithoutExt = match.group('fileWithoutExt').strip()
            logDebug('setValues', 'file name without extension %s', fileWithoutExt)
            summaryFilePath = fileWithoutExt + '.summary'
            logDebug('setValues', 'looking for summary file %s', summaryFilePath)
            # If the summary file exist read in the contents
            if os.path.exists(summaryFilePath) is True:
                log('setValues', 'episode summary file %s exists', summaryFilePath)
                self.episodeSummary = self.loadTextFromFile(summaryFilePath)
            else:
                log('setValues', 'episode summary file does not exist')

    def loadTextFromFile(self, filePath):
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
        # Iterate over the list of regular expressions
        for regex in self.getSupportedRegexes():
            # Find out what file format is being used
            match = re.search(regex, mediaFile, re.IGNORECASE)
            logDebug('parse', 'regex %s - matches: %s', regex, match)
            if match:
                logDebug('parse', 'found matches')
                self.setValues(mediaFile, match)
                break
  
    def findFile(self, filePath, fileNames):
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
                pathToFind = os.path.normcase(parentDir + '/' + fileName)
                logDebug('findFile', 'determining whether file %s exists', pathToFind)
                if os.path.exists(pathToFind) and os.path.isfile(pathToFind):
                    logDebug('findFile', 'file %s exists', pathToFind)
                    return pathToFind
                else:
                    logDebug('findFile', 'file %s does not exist', pathToFind)

            # go up a directory
            logDebug('findFile', 'going up a directory')
            newDir = os.path.abspath(parentDir + '/..')
            logDebug('findFile', 'new directory path %s', newDir)
            # if the new directory and parent directory are the same then we have reached the top directory - stop looking for the file
            if newDir == parentDir:
                logDebug('findFile', 'root directory %s found - stopping directory traversal', newDir)
                rootDirFound = True 
            else:
                parentDir = newDir
                
        return None
  
    def findSeasonSummary(self, filePath, fileNames):
        logDebug('findSeasonSummary', 'looking for files with names: %s', str(fileNames))
        filePath = self.findFile(filePath, fileNames)
        if filePath != None:
            log('findSeasonSummary', 'found season summary file %s', filePath)
            self.seasonSummary = self.loadTextFromFile(filePath)
        else:
            log('findSeasonSummary', 'season summary file not found')
            
        return self.seasonSummary

    def findShowSummary(self, filePath, fileNames):
        logDebug('findShowSummary', 'looking for files with names: %s', str(fileNames))
        filePath = self.findFile(filePath, fileNames)
        if filePath != None:
            log('findShowSummary', 'found file summary file %s', filePath)
            self.showSummary = self.loadTextFromFile(filePath)
        else:
            log('findShowSummary', 'show summary file not found')
            
        return self.showSummary
        
    def getEpisodeTitle(self):
        return self.episodeTitle

    def getEpisodeSummary(self):
        return self.episodeSummary

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
                r'(?P<showTitle>[^\\/]+)[\\/][sc|season|chapter]*?[ ]*?(?P<seasonNumber>[0-9]+)([-\. ]+(?P<seasonTitle>[^\\/]+)){0,1}[\\/][^\\/]*?[e](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$',
                #01 - Season Title\Show Title\Show Title - s2012e09 - Episode Title.mp4
                #01\Show Title\Show Title - s2012e09 - Episode Title.mp4
                r'[sc|season|chapter]*?[ ]*?(?P<seasonNumber>[0-9]+)([-\. ]+(?P<seasonTitle>[^\\/]+)){0,1}[\\/](?P<showTitle>[^\\/]+)[\\/][^\\/]*?[e](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$',
                #Show Title\01 - Season Title\09 - Episode Title.mp4 
                #Show Title\01\09 - Episode Title.mp4
                r'(?P<showTitle>[^\\/]+)[\\/][sc|season|chapter]*?[ ]*?(?P<seasonNumber>[0-9]+)([-\. ]+(?P<seasonTitle>[^\\/]+)){0,1}[\\/](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$',
                #01 - Season Title\Show Title\09 - Episode Title.mp4 
                #01\Show Title\09 - Episode Title.mp4
                r'[sc|season|chapter]*?[ ]*?(?P<seasonNumber>[0-9]+)([-\. ]+(?P<seasonTitle>[^\\/]+)){0,1}[\\/](?P<showTitle>[^\\/]+)[\\/](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$',
                #Show Title\2012\Show Title - s2012e09 - Episode Title.mp4
                #Show Title\2012\e09 - Episode Title.mp4 
                r'(?P<showTitle>[^\\/]+)[\\/][sc|season|chapter]*?[ ]*?(?P<seasonNumber>[0-9]+)[\\/][^\\/]*?[e](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$',
                #2012\Show Title\Show Title - s2012e09 - Episode Title.mp4
                #2012\Show Title\e09 - Episode Title.mp4 
                r'[sc|season|chapter]*?[ ]*?(?P<seasonNumber>[0-9]+)[\\/](?P<showTitle>[^\\/]+)[\\/][^\\/]*?[e](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$',
                #Show Title\2012\09 - Episode Title.mp4 
                r'(?P<showTitle>[^\\/]+)[\\/][sc|season|chapter]*?[ ]*?(?P<seasonNumber>[0-9]+)[\\/](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$',
                #2012\Show Title\09 - Episode Title.mp4 
                r'[sc|season|chapter]*?[ ]*?(?P<seasonNumber>[0-9]+)[\\/](?P<showTitle>[^\\/]+)[\\/](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$' 
                ] 

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
            r'(?P<showTitle>[^\\/]+)[\\/][sc|season|chapter]*?[ ]*?(?P<seasonNumber>[0-9]+)[\\/][e](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeYear>[0-9]{4})[-\. ](?P<episodeMonth>[0-9]{2})[-\. ](?P<episodeDay>[0-9]{2})[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$',
            #Show Title\s2015\e09 - 12-31-2015 - Episode Title.mp4
            r'(?P<showTitle>[^\\/]+)[\\/][sc|season|chapter]*?[ ]*?(?P<seasonNumber>[0-9]+)[\\/][e](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeMonth>[0-9]{2})[-\. ](?P<episodeDay>[0-9]{2})[-\. ](?P<episodeYear>[0-9]{4})[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$',
            #Show Title\e09 - 2015-12-31 - Episode Title.mp4
            r'(?P<showTitle>[^\\/]+)[\\/][e](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeYear>[0-9]{4})[-\. ](?P<episodeMonth>[0-9]{2})[-\. ](?P<episodeDay>[0-9]{2})[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$',
            #Show Title\e09 - 12-31-2015 - Episode Title.mp4
            r'(?P<showTitle>[^\\/]+)[\\/][e](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeMonth>[0-9]{2})[-\. ](?P<episodeDay>[0-9]{2})[-\. ](?P<episodeYear>[0-9]{4})[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$'
        ]
                 
def Start():
    log('Start', 'starting agents %s, %s', SERIES_AGENT_NAME)
    pass

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
        foundShowSummary = False

        for s in media.seasons:
            logDebug('update', 'season %s', s)
            seasonMetadata = metadata.seasons[s]
            logDebug('update', 'season metadata %s', seasonMetadata)
            metadata.seasons[s].index = int(s)
            foundSeasonSummary = False
          
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
                        log('update', 'parser object id: %s', id(parser))
                        log('update', 'parser %s contains match - parsing file path', parser)
                        parser.parse(absFilePath)
                        
                        # set the episode data
                        episodeMetadata.title = parser.getEpisodeTitle()  
                        episodeMetadata.summary = parser.getEpisodeSummary()
                        log('update', 'episode.title: %s', episodeMetadata.title)
                        log('update', 'episode.summary: %s', episodeMetadata.summary)
                        
                        # Check for show summary
                        if foundShowSummary is False:
                            showSummary = parser.findShowSummary(absFilePath, [showTitle + '.summary', 'show.summary'])
                            # set the show summary
                            if showSummary != None:
                                metadata.summary = showSummary
                                log('update', 'show.summary: %s', metadata.summary)
                                foundShowSummary = True

                        # Check for season summary
                        if foundSeasonSummary is False:
                            # set the season summary
                            seasonFileNames = [showTitle + '-S' + s + '.summary', showTitle + '-s' + s + '.summary', showTitle + '-C' + s + '.summary', showTitle + '-c' + s + '.summary', 'season-' + s + '.summary', 'chapter-' + s + '.summary', 'S' + s + '.summary', 's' + s + '.summary', 'C' + s + '.summary', 'c' + s + '.summary']
                            seasonSummary = parser.findSeasonSummary(absFilePath, seasonFileNames)
                            if seasonSummary != None:
                                seasonMetadata.summary = seasonSummary
                                log('update', 'season.summary: %s', seasonMetadata.summary)
                                foundSeasonSummary = True
                                                    
                        break
                    #endif
                #endfor - parsers
            #endfor - episodes
        #endfor - seasons
    #enddfe