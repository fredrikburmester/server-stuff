#!/usr/bin/env python3
from arrlib import RADARR_URL, RADARR_KEY, SONARR_URL, SONARR_KEY
import json, urllib.request, urllib.parse, urllib.error
URL=RADARR_URL; KEY=RADARR_KEY
PROFILE=6; ROOT="/movies"; HDRS={"X-Api-Key":KEY,"Content-Type":"application/json"}
def api(path, method="GET", body=None):
    data=json.dumps(body).encode() if body is not None else None
    req=urllib.request.Request(URL+path,data=data,headers=HDRS,method=method)
    with urllib.request.urlopen(req,timeout=30) as r: return json.loads(r.read().decode())

OVERRIDES={"WALL-E":10681}  # titles whose text-search misfires -> force by tmdbId

YEARS={
2000:["Mission: Impossible II","Gladiator","Cast Away","What Women Want","Dinosaur","How the Grinch Stole Christmas","Meet the Parents","The Perfect Storm","X-Men","What Lies Beneath"],
2001:["Harry Potter and the Philosopher's Stone","The Lord of the Rings: The Fellowship of the Ring","Monsters, Inc.","Shrek","Ocean's Eleven","Pearl Harbor","Jurassic Park III","Planet of the Apes","Hannibal","The Mummy Returns"],
2002:["The Lord of the Rings: The Two Towers","Harry Potter and the Chamber of Secrets","Spider-Man","Star Wars: Episode II - Attack of the Clones","Die Another Day","Signs","Men in Black II","My Big Fat Greek Wedding","Ice Age","Minority Report"],
2003:["The Lord of the Rings: The Return of the King","Finding Nemo","The Matrix Reloaded","Pirates of the Caribbean: The Curse of the Black Pearl","Bruce Almighty","The Last Samurai","Terminator 3: Rise of the Machines","The Matrix Revolutions","X2","Bad Boys II"],
2004:["Shrek 2","Harry Potter and the Prisoner of Azkaban","Spider-Man 2","The Incredibles","The Passion of the Christ","The Day After Tomorrow","The Bourne Supremacy","National Treasure","I, Robot","Troy"],
2005:["Harry Potter and the Goblet of Fire","Star Wars: Episode III - Revenge of the Sith","The Chronicles of Narnia: The Lion, the Witch and the Wardrobe","War of the Worlds","King Kong","Madagascar","Mr. & Mrs. Smith","Charlie and the Chocolate Factory","Batman Begins","Hitch"],
2006:["Pirates of the Caribbean: Dead Man's Chest","The Da Vinci Code","Ice Age: The Meltdown","Casino Royale","Night at the Museum","Cars","X-Men: The Last Stand","Mission: Impossible III","Superman Returns","Happy Feet"],
2007:["Spider-Man 3","Harry Potter and the Order of the Phoenix","Pirates of the Caribbean: At World's End","Transformers","The Bourne Ultimatum","National Treasure: Book of Secrets","I Am Legend","Ratatouille","300","Shrek the Third"],
2008:["The Dark Knight","Indiana Jones and the Kingdom of the Crystal Skull","Kung Fu Panda","Hancock","Mamma Mia!","Madagascar: Escape 2 Africa","Quantum of Solace","Iron Man","WALL-E","The Chronicles of Narnia: Prince Caspian"],
2009:["Avatar","Harry Potter and the Half-Blood Prince","Ice Age: Dawn of the Dinosaurs","Transformers: Revenge of the Fallen","2012","Up","The Twilight Saga: New Moon","Sherlock Holmes","Angels & Demons","The Hangover"],
2010:["Toy Story 3","Alice in Wonderland","Harry Potter and the Deathly Hallows: Part 1","Inception","Shrek Forever After","The Twilight Saga: Eclipse","Iron Man 2","Tangled","Despicable Me","How to Train Your Dragon"],
2011:["Harry Potter and the Deathly Hallows: Part 2","Transformers: Dark of the Moon","Pirates of the Caribbean: On Stranger Tides","The Twilight Saga: Breaking Dawn - Part 1","Mission: Impossible - Ghost Protocol","Kung Fu Panda 2","Fast Five","The Hangover Part II","The Smurfs","Cars 2"],
2012:["The Avengers","Skyfall","The Dark Knight Rises","The Hobbit: An Unexpected Journey","Ice Age: Continental Drift","The Twilight Saga: Breaking Dawn - Part 2","The Amazing Spider-Man","Madagascar 3: Europe's Most Wanted","The Hunger Games","Men in Black 3"],
2013:["Frozen","Iron Man 3","Despicable Me 2","The Hobbit: The Desolation of Smaug","The Hunger Games: Catching Fire","Fast & Furious 6","Monsters University","Gravity","Man of Steel","Thor: The Dark World"],
2014:["Transformers: Age of Extinction","The Hobbit: The Battle of the Five Armies","Guardians of the Galaxy","Maleficent","The Hunger Games: Mockingjay - Part 1","X-Men: Days of Future Past","Captain America: The Winter Soldier","Dawn of the Planet of the Apes","Big Hero 6","Interstellar"],
2015:["Star Wars: The Force Awakens","Jurassic World","Avengers: Age of Ultron","Furious 7","Minions","Inside Out","Spectre","Mission: Impossible - Rogue Nation","The Martian","Cinderella"],
2016:["Captain America: Civil War","Rogue One: A Star Wars Story","Finding Dory","Zootopia","The Jungle Book","The Secret Life of Pets","Batman v Superman: Dawn of Justice","Fantastic Beasts and Where to Find Them","Deadpool","Suicide Squad"],
2017:["Star Wars: The Last Jedi","Beauty and the Beast","The Fate of the Furious","Despicable Me 3","Jumanji: Welcome to the Jungle","Spider-Man: Homecoming","Wolf Warrior 2","Guardians of the Galaxy Vol. 2","Thor: Ragnarok","Wonder Woman"],
2018:["Avengers: Infinity War","Black Panther","Jurassic World: Fallen Kingdom","Incredibles 2","Aquaman","Bohemian Rhapsody","Venom","Mission: Impossible - Fallout","Deadpool 2","Fantastic Beasts: The Crimes of Grindelwald"],
2019:["Avengers: Endgame","The Lion King","Frozen II","Spider-Man: Far From Home","Captain Marvel","Joker","Star Wars: The Rise of Skywalker","Toy Story 4","Aladdin","Fast & Furious Presents: Hobbs & Shaw"],
2020:["The Eight Hundred","Demon Slayer: Mugen Train","Bad Boys for Life","My People, My Homeland","Tenet","Sonic the Hedgehog","Dolittle","Birds of Prey","The Croods: A New Age","Wonder Woman 1984"],
2021:["Spider-Man: No Way Home","The Battle at Lake Changjin","Hi, Mom","No Time to Die","F9","Detective Chinatown 3","Venom: Let There Be Carnage","Godzilla vs. Kong","Shang-Chi and the Legend of the Ten Rings","Eternals"],
2022:["Avatar: The Way of Water","Top Gun: Maverick","Jurassic World Dominion","Doctor Strange in the Multiverse of Madness","Minions: The Rise of Gru","The Batman","Black Panther: Wakanda Forever","Thor: Love and Thunder","Black Adam","Sonic the Hedgehog 2"],
2023:["Barbie","The Super Mario Bros. Movie","Oppenheimer","Guardians of the Galaxy Vol. 3","Fast X","Spider-Man: Across the Spider-Verse","The Little Mermaid","Mission: Impossible - Dead Reckoning Part One","Wonka","Ant-Man and the Wasp: Quantumania"],
2024:["Inside Out 2","Deadpool & Wolverine","Moana 2","Despicable Me 4","Dune: Part Two","Wicked","Kung Fu Panda 4","Godzilla x Kong: The New Empire","Beetlejuice Beetlejuice","Gladiator II"],
2025:["Ne Zha 2","Lilo & Stitch","A Minecraft Movie","Jurassic World Rebirth","How to Train Your Dragon","Mission: Impossible - The Final Reckoning","Superman","F1","Sinners","Thunderbolts"],
}

existing={m["tmdbId"] for m in api("/api/v3/movie")}
added,skipped,failed=[],[],[]
for year in sorted(YEARS):
    for title in YEARS[year]:
        try:
            if title in OVERRIDES:
                results=api(f"/api/v3/movie/lookup?term=tmdb:{OVERRIDES[title]}")
            else:
                results=api(f"/api/v3/movie/lookup?term={urllib.parse.quote(title)}")
            if not results: failed.append((year,title,"no lookup result")); continue
            cand=sorted(results,key=lambda r:abs((r.get("year") or 0)-year))
            best=next((r for r in cand if r.get("year")==year),cand[0])
            tmdb=best["tmdbId"]; chosen=f'{best["title"]} ({best.get("year")})'
            if tmdb in existing: skipped.append((year,chosen)); continue
            p=dict(best); p["qualityProfileId"]=PROFILE; p["rootFolderPath"]=ROOT
            p["monitored"]=True; p["addOptions"]={"searchForMovie":True}
            api("/api/v3/movie",method="POST",body=p); existing.add(tmdb)
            flag="" if best.get("year")==year else f"  [yr {best.get('year')} vs {year}]"
            added.append((year,chosen,flag))
        except urllib.error.HTTPError as e: failed.append((year,title,f"HTTP {e.code}: {e.read().decode()[:100]}"))
        except Exception as e: failed.append((year,title,str(e)[:100]))
print(f"\n=== ADDED ({len(added)}) ===")
for y,c,f in added: print(f" + {y}  {c}{f}")
print(f"\n=== SKIPPED/already have ({len(skipped)}) ===")
for y,c in skipped: print(f" = {y}  {c}")
print(f"\n=== FAILED ({len(failed)}) ===")
for y,t,w in failed: print(f" ! {y}  {t} - {w}")
