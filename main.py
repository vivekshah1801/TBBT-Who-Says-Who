#!/usr/bin/env python
# coding: utf-8

import requests
import xmltodict
from collections import defaultdict, Counter
from bs4 import BeautifulSoup

from schemas import Dialogue, Transcript, Scene

SITEMAP_URL = "https://bigbangtrans.wordpress.com/sitemap.xml"

def get_urls_for_transcripts(sitemap_url: str) -> list[str] :
    # Tried searching for subtitles with character names, but unable to find any reliable sources.
    # Found https://bigbangtrans.wordpress.com/series-1-episode-1-pilot-episode/ with transcribe while googling.
    # This blog has transcripts with somewhat sensible format, using sitemap for extract pages with transcript.
    res = requests.get(sitemap_url)
    sitemap_data = res.text
    sitemap_dict = xmltodict.parse(sitemap_data)
    sitemap_dict.get('url')
    urls = [x.get('loc') for x in sitemap_dict.get('urlset').get('url')]
    urls = [x for x in urls if "series-" in x] # based on pattern in url
    return urls

def download_transcripts_metadata_and_html(urls: list[str]) -> list[Transcript]:
    transcripts: list[Transcript] = []
    for url in urls:
        # Based on observed patterns of urls
        # i.e. https://bigbangtrans.wordpress.com/series-1-episode-1-pilot-episode/
        scheme, _, site, path, _ = url.split("/")
        _, season, _, episode, title = path.split("-", maxsplit=4)
        # Downloading html content
        html_text = ""
        res = requests.get(url)
        if res.status_code == 200:
            html_text = res.text
        transcript = Transcript(season=int(season), episode=int(episode), title=title, link=url, html_text=html_text)
        transcripts.append(transcript)
    return transcripts

def parse_transcript_text(html_text: str) -> str:
    soup = BeautifulSoup(html_text, 'lxml')
    # Blog content is in div with id `content` [Checked via inspect element]
    raw_text = soup.select('#content')[0].text
    return raw_text

def parse_text_from_transcripts(transcripts: list[Transcript]) -> list[Transcript]:
    for transcript in transcripts:
        print(f"Extracting text from HTML for {transcript.link}")
        transcript.raw_text = parse_transcript_text(transcript.html_text)
    return transcripts

def extract_dialogues_from_transcripts(transcripts: list[Transcript]) -> list[Dialogue]:
    dialogues = []
    for transcript in transcripts:
        lines = [x for x in transcript.raw_text.split("\n") if x]
        for line in lines:
            try:
                speaker, text = line.split(":", maxsplit=1)
                dialogue = Dialogue(speaker=speaker, text=text, transcript=transcript)
                dialogues.append(dialogue)
            except Exception as e:
                pass
    return dialogues

def segregate_scenes_and_dialogues(all_dialogues: list[Dialogue]) -> (list[Dialogue], list[Scene]):
    # scenes are added in transcript with format `scene: Description`
    # In out case it is parsed as dialogue with speaker = scene.
    dialogues, scenes = [], []
    for dialogue in all_dialogues:
        if dialogue.speaker.lower() == 'scene':
            scene = Scene(description=dialogue.text, transcript=dialogue.transcript)
            scenes.append(scene)
        else:
            dialogues.append(dialogue)
    return dialogues, scenes

def clean_up_speaker_names(dialogues: list[Dialogue]) -> list[Dialogue]:
    # Clean up: There are many speaker parsed as `speaker_name (blah-blah)`
    # Adding information in bracket as speaker_supporting_text in dialogue
    for i, dialogue in enumerate(dialogues):
        original_speaker = dialogue.speaker.lower().strip()
        if "(" in original_speaker or "(" in original_speaker:
            speaker, speaker_supporting_text = original_speaker.split("(", maxsplit=1)
            speaker = speaker.strip()
            speaker_supporting_text = speaker_supporting_text.replace(")","").replace("(","").strip()
        else:
            speaker = original_speaker
            speaker_supporting_text = ""
        dialogue.speaker = speaker
        dialogue.speaker_supporting_text = speaker_supporting_text
    return dialogues

def get_speaker_dialogue_counter(dialogues: list[Dialogue]) -> Counter:
    dialogues_per_speaker = defaultdict(int)
    for dialogue in dialogues:
        dialogues_per_speaker[dialogue.speaker] += 1
    from collections import Counter
    dialogues_per_speaker = Counter(dialogues_per_speaker)
    return dialogues_per_speaker


def rename_speaker_names(dialogues: list[Dialogue]) -> list[Dialogue]:
    # Based on the dialogues_per_speaker Counter instance,
    # some speaker names are mistyped and misattributes.
    # Creating a dictionary to fix them
    speaker_rename_dict = {
        # Since we have both barry and kripke in the set, keeping only kripke to make it consistent
        'barry': 'kripke',
        'past sheldon': 'sheldon',
        'past leonard': 'leonard',
        'mary': 'mrs cooper',
        'howard’s mother': 'mrs wolowitz',
        'lesley': 'leslie',
        'beverly': 'beverley',
        'wil wheaton': 'wil',
        'penny’s dad': 'wyatt',
        'stephen hawking': 'hawking',
        # I am considering only these, others have only <20 instances
    }
    for dialogue in dialogues:
        dialogue.speaker = speaker_rename_dict.get(dialogue.speaker, dialogue.speaker)
    return dialogues


def get_count_of_word_said_by_speaker(dialogues: list[Dialogue], speaker: str, word: str) -> int:
    speaker, word = speaker.lower(), word.lower()
    word_count = 0
    for dialogue in dialogues:
        if dialogue.speaker == speaker:
            word_count += dialogue.text.lower().count(word)
    return word_count

if __name__ == "__main__":
    print("Getting urls for the transcripts")
    urls = get_urls_for_transcripts(sitemap_url=SITEMAP_URL)
    print(f"Got {len(urls)} urls for transcripts, Downloading HTML")
    transcripts = download_transcripts_metadata_and_html(urls)
    print(f"Got {len(transcripts)} transcripts, parsing them")
    transcripts = parse_text_from_transcripts(transcripts)
    print(f"Extracting dialogues from transcripts")
    dialogues = extract_dialogues_from_transcripts(transcripts)
    print(f"Got {len(dialogues)} dialogues and scenes")
    dialogues, scenes = segregate_scenes_and_dialogues(dialogues)
    print(f"Segregated into {len(dialogues)} dialogues and {len(scenes)} scenes")
    # Exploration
    # print(f"Speakers: {list(set([x.speaker.lower() for x in dialogues]))}")
    # print(f"Speaker Dialogue count: {get_speaker_dialogue_counter(dialogues)}")
    print(f"Cleaning speaker names")
    dialogues = clean_up_speaker_names(dialogues)
    print("Renaming speaker names to avoid duplicates")
    dialogues = rename_speaker_names(dialogues)
    # Big Question: How many times sheldon says the word `penny`
    speaker = 'sheldon'
    word = 'penny'
    word_count = get_count_of_word_said_by_speaker(dialogues, speaker=speaker, word=word)
    print(f"ANS: {speaker.title()} says the word `{word}` {word_count} times")

