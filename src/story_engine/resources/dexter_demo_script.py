"""The rehearsed demo's prose, authored beat by beat and replayed verbatim on stage.

Keyed by the turn loop's idempotency key, `"{knower}:{chapter}:{visible_fact_count}"`. The key is
not incidental — it names *who is looking, when, and how much they are entitled to see*, which is
exactly the axis the demo turns on. The same branch keyed for `dexter` and for `deborah` cannot
collide, because they are not looking at the same world.

**Every beat here is written strictly inside its own view.** The counts are what the guard actually
returned for the rehearsed path:

    dexter    ch1..ch6 -> 2, 4, 5, 6, 7, 9 facts
    deborah   ch1..ch6 -> 0, 1, 2, 2, 3, 4 facts

Deborah stalls at **2 across chapters 3 and 4** — the turn where Doakes ends up in the room and
learns what Dexter is adds *nothing at all* to her view. Her chapter-4 beat is written to sit in
that hole: she knows a night happened, and she does not know what it contained. If a future edit
makes her narration knowing there, the demo has quietly stopped being true.

Prose follows `prompts/render_scene/v1.jinja`: second person, present tense, no naming of the
options. A beat with no scripted entry falls back to `ScriptedLLM._compose`, which is deliberately
mechanical so a gap is visible rather than plausible.
"""

DEXTER_RUN: dict[str, str] = {
    "dexter:1:2": (
        "The moon is doing that thing again — too full, too bright, too interested. You have been "
        "careful for three weeks about this priest, because careful is the whole of it. Harry made "
        "the rules and Harry made you, and the rules are not suggestions; they are the reason you "
        "are a blood-spatter analyst with a tidy apartment instead of a case file with your name "
        "on the spine. Be sure. Be exact. Take the extra time.\n\n"
        "You are sure. You have been sure for days, and the certainty sits in you like a held "
        "breath.\n\n"
        "Somewhere under the ribs, the Dark Passenger stretches and makes its small polite noise, "
        "the one that means *now* and has never once been wrong. Miami is warm and loud and "
        "entirely uninterested in either of you. The night is wide open.\n\n"
        "It comes down to what you do with it."
    ),
    "dexter:2:4": (
        "Morning does what mornings do — it makes the previous night look like something you read "
        "about. The priest is finished. Careful, exact, the Harry way; nothing left that says "
        "anything to anyone who knows how to read it, and you are the one they send to read it.\n\n"
        "There is a message blinking. Tinny Tejano music, then Deborah, who is your foster sister "
        "and a cop like her father was a cop, saying your name twice the way she does when she is "
        "already halfway to angry.\n\n"
        "Deborah is one of the very few people who has things to say to you. This is not nothing. "
        "You have built an entire life out of being pleasant and blank, and she keeps talking to "
        "you anyway, as if there were someone in here.\n\n"
        "Her voice is still going. You have not decided yet how much of you is going to answer it."
    ),
    "dexter:3:5": (
        "Deborah is in the car beside you and the case is now a thing you are both holding, which "
        "is new. She talks the whole way — about the department, about what LaGuerta will say, "
        "about what she wants to be instead of what they keep making her be.\n\n"
        "You are excellent at this. You nod at the correct intervals. You make the small human "
        "noises. Nobody has ever caught you at it, and it has never once felt like lying, because "
        "lying implies there is a truth underneath being covered up, and mostly there is only the "
        "quiet.\n\n"
        "The priest is three days cold and completely invisible. Deborah does not know. Deborah "
        "will never know, because Harry built the rules around exactly this — around her, really, "
        "if you think about it too long, which you try not to.\n\n"
        "She turns to ask you something. The next part is yours."
    ),
    "dexter:4:6": (
        "Doakes has been behind you for eleven minutes.\n\n"
        "He does not pretend otherwise. He never has. From the first day he looked at you the way "
        "a dog looks at a snake — no evidence, no theory, no probable cause, just an animal "
        "certainty that something in the room is wrong and it is standing near the coffee.\n\n"
        "The Passenger is very still. Not afraid. Interested.\n\n"
        "There is a moment — a short one, with a shape you can feel the edges of — where the "
        "distance between his headlights and your mirror stops being a distance and becomes a "
        "decision. Harry's voice says *be careful, be exact*, and Harry's voice has never once "
        "accounted for a man who simply knows.\n\n"
        "The lot is empty. The lights are the orange of every bad hour you have ever had.\n\n"
        "He is getting out of the car."
    ),
    "dexter:5:7": (
        "Rita has made a casserole and set the table for four, and this is the part you are "
        "genuinely good at.\n\n"
        "She is as badly damaged as you are, which is the entire reason it works. She does not "
        "want the things people usually want. She wants an ordinary evening, repeated, "
        "indefinitely — and an ordinary evening is a performance, and a performance is the one "
        "thing you can do perfectly.\n\n"
        "So you eat. You compliment the casserole, which does not need it. You laugh at the right "
        "half-second.\n\n"
        "Underneath the table your hands are steady, because they always are, and somewhere across "
        "town a very large man is sitting with something he saw and has not yet decided what to do "
        "with. That is a fact now. It sits in the room with the casserole.\n\n"
        "Rita asks if you are all right. You are, mostly. You always are."
    ),
    "dexter:6:9": (
        "It closes the way these things close: quietly, and entirely on your terms.\n\n"
        "You did it careful. You did it exact. Harry would have hated every part of the reason and "
        "approved of every part of the method, which is the closest thing to a blessing you were "
        "ever going to get.\n\n"
        "Take an inventory, then. Deborah is inside the case now and thinks that was her doing. "
        "Rita believes she spent an ordinary evening with an ordinary man. Doakes is carrying "
        "something he cannot say out loud without sounding insane, and he knows it, and that is "
        "its own kind of cage.\n\n"
        "Four people, four different versions of the same week, and only one of them is complete.\n\n"
        "The moon is going down. The Passenger is quiet and pleased and not remotely finished.\n\n"
        "Neither, it turns out, are you."
    ),
}

DEBORAH_REPLAY: dict[str, str] = {
    # Zero facts. She is not in this scene, she has not been told about it, and she cannot infer
    # it. The beat has to be *about* the absence — anything atmospheric she has not earned would
    # be the renderer inventing knowledge.
    "deborah:1:0": (
        "You are working a shift that will not end and thinking about nothing in particular.\n\n"
        "Somewhere in this city it is a Tuesday. That is the whole of what you have got.\n\n"
        "Later — much later — you will go back over this night and try to find the seam in it, the "
        "place where you should have noticed something. You will not find one. There is nothing "
        "here to notice. There is a moon, and there is work, and there is a brother you would "
        "describe, without hesitating, as the most harmless man you know."
    ),
    "deborah:2:1": (
        "You leave him a message and it goes the way your messages to Dexter always go — into "
        "whatever quiet place he keeps, to be answered eventually, pleasantly, and slightly beside "
        "the point.\n\n"
        "He is your foster brother. You are a cop, like Harry was, which is either a tribute or a "
        "sentence depending on the day. Dexter is the one who does not flinch when you talk about "
        "the job, and after enough years you stop asking why and just start being grateful.\n\n"
        "You say his name twice on the recording. You are already halfway to angry, which is your "
        "resting state where he is concerned, and which he has never once held against you.\n\n"
        "Then you go back to work, because that is what there is."
    ),
    "deborah:3:2": (
        "He picks you up and lets you in on it, and you spend the drive talking more than you meant "
        "to — about the department, about LaGuerta, about the thing you want to be instead of the "
        "thing they keep assigning you to be.\n\n"
        "Dexter listens. He always listens. He makes the small agreeing noises in the right places "
        "and asks the question you were hoping someone would ask.\n\n"
        "It occurs to you, briefly, that you have no idea what he does with his evenings. It "
        "occurs to you the way a draft does — you notice it, you adjust, you forget it.\n\n"
        "You turn to ask him something."
    ),
    # STILL two facts. This is the chapter where Doakes ends up in the lot and learns what her
    # brother is, and it lands in her view as absolutely nothing. The beat is written to sit in
    # that hole on purpose.
    "deborah:4:2": (
        "You do not see him for a day and a half.\n\n"
        "This is not unusual. Dexter keeps hours that belong to no schedule you have ever been "
        "able to name, and when you ask he says something about the boat, or the lab, or nothing "
        "much, and you let it go, because the alternative is interrogating the one person who has "
        "never given you a reason to.\n\n"
        "The case does not move. You reread the same file until the words come apart.\n\n"
        "Somewhere in those thirty-six hours something happened that would rearrange your entire "
        "understanding of your family, and you spend them annoyed about paperwork.\n\n"
        "You will not learn about it in this chapter. Or the next one."
    ),
    "deborah:5:3": (
        "Dexter has dinner with Rita, and you hear about it the way you hear about everything in "
        "his life — afterwards, in summary, and pleasantly.\n\n"
        "You like Rita. You like that she exists. She is proof of a version of your brother that "
        "you can hold on to without effort: a slightly awkward man who is kind to a woman who has "
        "had very little kindness, and who is, if anything, a bit boring about it.\n\n"
        "You have a theory that Dexter is lonelier than he lets on. It is a good theory. It fits "
        "everything you have ever observed.\n\n"
        "It is also wrong in a direction you have not got the imagination for, and nothing in this "
        "week is going to correct it."
    ),
    "deborah:6:4": (
        "It ends and you are told that it ended.\n\n"
        "Here is what you have got: a case that closed, a brother who was helpful throughout, a "
        "woman named Rita who is good for him, and a fortnight that hangs together perfectly as "
        "long as nobody asks a harder question than the ones you asked.\n\n"
        "Doakes has been looking at you strangely. You assume it is about you. It has never once "
        "been about you.\n\n"
        "You go home. You sleep well, actually — better than you have in weeks.\n\n"
        "This is the same fortnight Dexter just walked you through. Same nights, same choices, "
        "same city. You were standing next to almost all of it.\n\n"
        "You know four things about it. He knows nine."
    ),
}

DEMO_SCRIPT: dict[str, str] = {**DEXTER_RUN, **DEBORAH_REPLAY}
"""The full rehearsed path. `tests/e2e/test_demo_script.py` asserts every beat is covered, so a
silent fall-through to the mechanical composer cannot reach the stage unnoticed."""
