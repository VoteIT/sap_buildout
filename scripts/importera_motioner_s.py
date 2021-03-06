# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import argparse
import csv
from webhelpers.html.converters import nl2br

from arche.utils import generate_slug, utcnow
from pyramid.paster import bootstrap
import transaction
from datetime import timedelta

USER = 'motionar'


def unicode_csv_reader(utf8_data, **kwargs):
    csv_reader = csv.reader(utf8_data, **kwargs)
    for row in csv_reader:
        yield [unicode(cell, 'utf-8') for cell in row]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config_uri", help="Paster ini file to load settings from")
    parser.add_argument("meeting_name", help="Möte att importera till")
    parser.add_argument("file_name", help="CSV-fil att importera")
    args = parser.parse_args()
    env = bootstrap(args.config_uri)
    root = env['root']
    request = env['request']
    meeting = root[args.meeting_name]


    csvfile = open(args.file_name, 'r')
    csvreader = unicode_csv_reader(csvfile, delimiter=str(";"))

    # Dumpa första raden
    csvreader.next()

    #0 gruppnamn ("Arbete")
    #1 Grupp (beteckning) ("A")
    #2 Nr ("1")
    #3 Motionstitel
    #4 Motionär (Förening)
    #5 Motionstext (+ nl2br)
    #6 yrkanderubrik (kasta?)
    #7 yrkanden, med siffra först ett per rad. Formatera
    #8 Motionen antagen/avslagen

    tags = set()
    current_tag = None
    for row in csvreader:
        tags.add(row[0])
        if current_tag != row[0]:
            if row[0]:
                #Create a new section first
                stripped_title = "".join(row[0].split()[1:])  # Remove leading "A. "
                ai = request.content_factories['AgendaItem'](
                    title="%s) %s" % (row[1], stripped_title),
                    tags = (row[0],),
                )
                name = generate_slug(meeting, ai.title)
                meeting[name] = ai
            current_tag = row[0]

        body = row[5]
        body += "<hr/>"
        body += "Motionär(er): " + row[4]
        # body += "\nHanterad av: " + row[11]
        ai = request.content_factories['AgendaItem'](
            title="%s%s) %s" % (row[1], row[2], row[3]),
            tags=(row[0],),
            body = nl2br(body).unescape()
        )
        name = generate_slug(meeting, ai.title)
        meeting[name] = ai

        offset = 0
        for attsats in row[7].splitlines():
            #Kasta första sektionen, som bara är siffra
            txt = " ".join(attsats.split(" ")[1:]).strip()
            created = utcnow() + timedelta(seconds=offset)
            offset += 2
            prop = request.content_factories['Proposal'](
                body = nl2br(body),
                created = created,
                text = txt,
                creator=[USER],
            )
            ai[prop.uid] = prop

    meeting.tags = tags
    print("Meeting imported, committing to database...")
    transaction.commit()
    env['closer']()


if __name__ == '__main__':
    main()
