export function to_ul(s: string[]) {
  let ret = "";
  for (const item of s) ret += `<li>${item}</li>`;
  return `<ul>${ret}</ul>`;
}

export function to_table(s: string[]) {
  let ret = "";
  for (const item of s) ret += `<tr>${item}</tr>`;
  return `<table><tbody>${ret}</tbody></table>`;
}

const wisdoms = [
  "always kan",
  "bad waits win games",
  "but i had 8 dora",
  "but they had a worse wait",
  "couldn't win a single game",
  "couldn't win a single hand",
  "game is rigged man",
  "how do i defend against dama",
  "i dealt in on purpose",
  "it was just a practice game",
  "it was safe last turn though",
  "luck-based game",
  "my draws were so bad",
  "never not riichi",
  "should have won that hand",
  "should've folded",
  "should've just drawn better tiles",
  "should've pushed",
  "shouldn't have called",
  "shouldn't have changed waits",
  "stupid luck-based tsumos",
  "suji traps are for amateurs",
  "that's mahjong for you",
  "they were in the dead wall",
  "used up all my luck too",
  "was in iishanten all game",
  "what were those garbage waits",
  "when i'm in tenpai, i deal in",
  "why doesn't anyone fold these days",
  "why even practice efficiency",
  "winners don't care about safety",
  "worst starting hands of my life",
]

export function get_wisdom() {
  return wisdoms[Math.floor(Math.random() * wisdoms.length)];
}

const sophistries = [
  "absolutely deserved",
  "as expected of a riichi player",
  "but have you tried skill",
  "dora just comes to me",
  "efficiency just means drawing good",
  "every draw was planned for",
  "fortune favors the bold, not the fold",
  "hell waits more like swell waits",
  "i don't read hands, i write them",
  "i exude dealer energy",
  "i'm not lucky, you're just predictable",
  "imagine being afraid of dealer riichi",
  "imagine drawing worse than iishanten",
  "imagine having less than 100k points",
  "imagine having less than 3 dora",
  "imagine keeping so called 'safe tiles'",
  "imagine playing safe when you can just win",
  "it was all part of the plan",
  "it's called getting good",
  "it's only a yakuman",
  "just as expected",
  "just draw better tiles",
  "let the scores speak for themselves",
  "never not riichi ippatsu tsumo",
  "real winners play the mind game",
  "skill-based game",
  "that game was all skill",
  "that was all calculated",
  "that was merely a 5-sided wait",
  "that's why i changed waits",
  "you just gotta manifest the tiles",
  "you say danger, i say profit",
]

export function get_sophistry() {
  return sophistries[Math.floor(Math.random() * sophistries.length)];
}