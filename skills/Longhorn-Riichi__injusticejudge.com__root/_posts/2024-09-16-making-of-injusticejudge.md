---
layout: blog
title: the making of injusticejudge
---

<header>
  <h2>{{ page.title }}</h2>
</header>

The idea came about in August 2023 during a discussion with my then-roommate Peter [(his website)](https://peterish.com) about rare unlucky bullshit that happens in mahjong games, like getting chased by a hell wait and dealing into said hell wait. The idea came to enumerate a list of such bullshit, but before we would do that, the obvious follow-up was, what if we built a bullshit detector?

> 👉😎👉 👈😃👈 --- ayo???

The original such detector (already named InjusticeJudge at the time) grew to become ~500 lines of Python code. It would parse a [tenhou.net](https://tenhou.net) game and give it to a function called `evaluate_unluckiness`, which did a bunch of ad-hoc checks for the following unlucky events to print to the command line:

- your tenpai was chased with a worse wait and they won
- your tenpai was chased with a worse wait and you dealt in (on top of the above)
- (if no other injustices exist) you dealt into someone
- (if no other injustices exist) you got chased

The output looked something like this:

```
Major unluckiness detected in East 2: your wait 🀊🀍 (5 ukeire) was chased
  by a worse wait 🀝 (2 ukeire), and you dealt into it
```

And so the time came to enumerate a list of unlucky events. As a result, `evaluate_unluckiness` became more and more complex, checking for more and more things in order to report the following events:

- someone won on the first row
- big tenpai hand destroyed by a dama low value hand
- iishanten hell
- riichi ippatsu tsumo
- placement drop due to oyakaburi

This was the start for many more checks to come.

### InjusticeJudge 2

At some point the name for unlucky events naturally settled on "injustices" (given that the project name was already called "InjusticeJudge") and more importantly, `evaluate_unluckiness` was starting to look like a thousand-line function. In order to make development of the detector less of a worsening train wreck, we needed a different way of going about things.

Each injustice check actually involves multiple checks. For instance, to check if one dealt into a player that chased their tenpai with a worse wait, one would need to 1) check that we're tenpai 2) check that someone was tenpai after us 3) check that their wait is worse, and 4) check that we dealt in. Each injustice brought with it a different combination of checks, some overlapping, and the insight was that we only need to check each check once.

So the solution was this. Rather than check for injustices directly, the evaluator function would check for the existence of certain events like "you lost points this round", "you were first to tenpai this round" etc. Then we can label certain combinations of these events as injustices.

This led to the following much more modular syntax of declaring an injustice:

```
# Print if your tenpai got chased by a worse wait, and you dealt in
@injustice([Flags.YOU_TENPAI_FIRST, Flags.YOU_GOT_CHASED,
            Flags.GAME_ENDED_WITH_RON,
            Flags.YOU_LOST_POINTS, Flags.CHASER_GAINED_POINTS,
            Flags.CHASING_PLAYER_HAS_WORSE_WAIT])
def dealt_into_chaser_with_worse_wait(flags, data, round_name):
    your_data = data[flags.index(Flags.YOU_TENPAI_FIRST)]
    chaser_data = data[flags.index(Flags.YOU_GOT_CHASED)]
    your_wait = your_data["wait"]
    chaser_wait = chaser_data["wait"]
    your_ukeire = your_data["ukeire"]
    chaser_ukeire = chaser_data["ukeire"]
    print(f"Major unluckiness detected in {round_name}:"
          f" your wait {ph(your_wait)} ({your_ukeire} ukeire)"
          f" was chased by a worse wait {ph(chaser_wait)}"
          f" ({chaser_ukeire} ukeire), and you dealt into it")
```

The result was that `evaluate_unluckiness` was split into two parts. `determine_flags` handled all the game logic figuring. This left the majority of the code, involving the composition of checks and formatting the output, as individual `@injustice` functions. Now we're in business. Working at an accelerated pace, within the course of two weeks the following injustices were added:

- you failed to improve your shanten for at least nine consecutive draws
- you started with 5 shanten and never got to tenpai
- you lost points to a first row ron/tsumo
- you dealt into dama
- you dealt into ippatsu
- someone else won with bad wait ippatsu tsumo
- you just barely failed nagashi
- someone calls your last tile for nagashi (not ron)
- you are dealer and was hit by baiman+ oyakaburi
- your riichi/tenpai tile dealt in
- you drew a tile that would have completed a past wait
- you dealt in while tenpai, right before you would have received tenpai payments
- you dealt into ura 3 OR if someone else tsumoed and got ura 3
- you dealt into haitei
- winner drew haitei or got houtei, while you were in tenpai
- winner had 3+ dora in closed part of hand

A lot of these injustices would be changed over time, but the essential idea behind all of them stayed the same: unlucky events that are just rare enough to be funny.

Mahjong Soul support was also added at this time.

### Beyond injustices

A few days later InjusticeJudge was integrated into Ronhorn, the Discord bot for the Riichi mahjong club [Longhorn Riichi](https://longhornriichi.com) based in Austin, TX. This was kind of an end goal of the project --- rather than having it remain a command line tool, allow Discord users to share/complain about injustices with each other directly in Discord.

With the advent of `/injustice` on Discord, however, an question emerged --- what about its counterpart `/justice`? What if I want to brag about being chased by a worse wait but with me winning, as is justified? This lead to some heated discussion of whether this was even a good idea. The obvious con to `/justice` is that it would be inflammatory for no reason, and so this idea was tabled and later scrapped.

Instead, the discussion came to the idea of unlucky events vs lucky events. For instance, chasing a tenpai player and winning is lucky, but being the victor doesn't give the classic mahjong feeling of bullshit that we love to see. That would be things like winning ippatsu tsumo, or calling kan for 4 dora, or winning a hell wait. And so `/skill` was born, showcasing such skillful feats of mahjong such as:

- starting iishanten
- dealing dangerous discards without dealing in
- not drawing any useless tiles before tenpai
- pon pon ron
- achieving tenpai with last draw (for noten payments)
- any yakuman tbh

Unlike the proposed `/justice`, showcasing moments of pure skill like these captures the _really funny_ "unjust" moments in mahjong, which is the point of the project anyways. So now we have yin and yang: `/injustice` for extreme unfair unluckiness, and `/skill` for extreme unfair luckiness. The date is September 2023.

### Recap

It is now a year later (September 2024) and the project has come a long way:

- many more injustices and skills
- enough injustices so that <1% of unjust-feeling games report zero injustices
- Riichi City support
- injusticejudge.com (this site)
- `/injustice` and `/skill` buttons directly available for Longhorn Riichi game results

In the absence of new injustice/skill suggestions [(suggestion box)](https://github.com/Longhorn-Riichi/InjusticeJudge/issues/1), the project is essentially complete. Thanks for reading!
