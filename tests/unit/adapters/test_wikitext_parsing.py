"""Unit tests for MediaWiki markup parsing — no network.

The fixture is a trimmed copy of the real `dexter.fandom.com` "Brian Moser" wikitext as fetched
2026-07-25, keeping the shapes that actually broke naive parsing: a decoy `CharacterPicture` template
before the real infobox, a `<gallery>` whose captions contain `|`, `<small>(role)</small>` inside a
`<br>`-separated list, a `{{Q|...}}` quote box ahead of the lead, and bolded links in the lead.
"""

from story_engine.adapters.outbound.wiki import wikitext

BRIAN_WIKITEXT = """{{Tabs (Brian Moser)}}
{{CharacterPicture
|photo       = 2013-09-14 1444.png
|name        = Brian Moser
|description = a.k.a. Ice Truck Killer
}}
{{DualProfile
|name             = Brian Moser
|image            = <gallery>
brianmoser1.png|2006
KidBianCloseup1.png|1974
</gallery>
|full name        = '''Brian Moser'''
|aliases          = '''[[Rudy Cooper (Alias)|Rudy Cooper]]'''
|status           = '''Deceased'''
|gender           = '''Male'''
|spouse           = '''None'''
|relatives        = '''[[Dexter Morgan]] <small>(younger brother/killer)</small>'''<br>
'''[[Laura Moser]] <small>(mother; deceased)</small>'''<br>
'''Cecilia (unseen aunt)'''
|profession       = '''Prosthetist'''<br>'''[[Serial Killer]]'''
|first_appearance = '''[[Episode 105: Love American Style|Love American Style]]'''
}}

{{Q|You can't be a killer and a hero. ~ Brian Moser}}

'''Brian Moser''', also known as '''The Ice Truck Killer''' or '''Rudy Cooper''', is a recurring
character and the '''secondary antagonist''' of [[Showtime|Showtime's]] '''''[[Dexter (show)|DEXTER]]'''''.

He also appears in the '''Dexter Novels''', where he is known as the '''Tamiami Slasher'''.

==Description==
Brian is a rather tall man with curly black hair.
"""


class TestParseTemplates:
    def test_finds_top_level_templates_only(self) -> None:
        names = [t.name for t in wikitext.parse_templates(BRIAN_WIKITEXT)]
        assert "DualProfile" in names
        assert "CharacterPicture" in names
        assert "Q" in names

    def test_selects_the_profile_over_the_decoy_picture_template(self) -> None:
        profile = wikitext.select_profile_template(
            wikitext.parse_templates(BRIAN_WIKITEXT)
        )
        assert profile is not None
        assert profile.name == "DualProfile"
        assert profile.params["status"] == "'''Deceased'''"

    def test_gallery_pipes_do_not_swallow_later_parameters(self) -> None:
        # A `<gallery>` caption contains `|`, which naive splitting treats as a parameter boundary.
        profile = wikitext.select_profile_template(
            wikitext.parse_templates(BRIAN_WIKITEXT)
        )
        assert profile is not None
        assert "full name" in profile.params
        assert "relatives" in profile.params

    def test_returns_no_profile_when_nothing_looks_like_one(self) -> None:
        templates = wikitext.parse_templates("{{Stub}}{{Navbox|left=a|right=b}}")
        assert wikitext.select_profile_template(templates) is None


class TestLeadSection:
    def test_drops_infobox_and_quote_box_and_stops_at_first_heading(self) -> None:
        lead = wikitext.lead_section(BRIAN_WIKITEXT)
        assert lead.startswith("Brian Moser, also known as The Ice Truck Killer")
        assert "Deceased" not in lead  # infobox parameters must not leak into prose
        assert (
            "rather tall man" not in lead
        )  # the ==Description== section is not the lead

    def test_resolves_piped_links_to_their_display_text(self) -> None:
        assert "Showtime's" in wikitext.lead_section(BRIAN_WIKITEXT)


class TestLeadAliases:
    def test_keeps_alternative_names_from_the_opening_paragraph(self) -> None:
        aliases = wikitext.lead_aliases(wikitext.lead_wikitext(BRIAN_WIKITEXT))
        assert "The Ice Truck Killer" in aliases
        assert "Rudy Cooper" in aliases

    def test_rejects_bolded_links_because_they_name_other_entities(self) -> None:
        aliases = wikitext.lead_aliases(wikitext.lead_wikitext(BRIAN_WIKITEXT))
        assert "DEXTER" not in aliases

    def test_rejects_narrative_roles_and_later_paragraphs(self) -> None:
        aliases = wikitext.lead_aliases(wikitext.lead_wikitext(BRIAN_WIKITEXT))
        assert "secondary antagonist" not in aliases
        assert "Dexter Novels" not in aliases
        assert "Tamiami Slasher" not in aliases  # second paragraph

    def test_rejects_a_bare_rank(self) -> None:
        assert wikitext.lead_aliases("'''Captain''' is a rank.") == ()


class TestParseEntityLinks:
    def test_parses_linked_target_with_a_small_tag_role(self) -> None:
        profile = wikitext.select_profile_template(
            wikitext.parse_templates(BRIAN_WIKITEXT)
        )
        assert profile is not None
        pairs = wikitext.parse_entity_links(profile.params["relatives"])
        assert ("Dexter Morgan", "younger brother/killer") in pairs
        assert ("Laura Moser", "mother; deceased") in pairs

    def test_keeps_an_unlinked_entry(self) -> None:
        # A name the wiki never gave a page is still a name the story must not contradict.
        pairs = wikitext.parse_entity_links("'''Cecilia (unseen aunt)'''")
        assert pairs == (("Cecilia", "unseen aunt"),)

    def test_drops_null_values(self) -> None:
        assert wikitext.parse_entity_links("'''None'''") == ()
        assert wikitext.parse_entity_links("Unknown<br>N/A") == ()

    def test_splits_on_break_tags(self) -> None:
        pairs = wikitext.parse_entity_links("[[A]] (x)<br>[[B]] (y)")
        assert [target for target, _ in pairs] == ["A", "B"]


class TestParseAliases:
    def test_strips_parentheticals_and_markup(self) -> None:
        assert wikitext.parse_aliases(
            "'''Rita Ann Morgan (née Brandon)'''<br>'''Rita Bennett (2nd marriage)'''"
        ) == ("Rita Ann Morgan", "Rita Bennett")

    def test_resolves_a_piped_link_to_its_display_text(self) -> None:
        assert wikitext.parse_aliases("[[Rudy Cooper (Alias)|Rudy Cooper]]") == (
            "Rudy Cooper",
        )


class TestCleanValue:
    def test_flattens_markup_to_one_line(self) -> None:
        assert wikitext.clean_value("'''[[Serial Killer]]'''<br>'''Prosthetist'''") == (
            "Serial Killer Prosthetist"
        )

    def test_recognizes_null_sentinels(self) -> None:
        assert wikitext.is_null_value("None")
        assert wikitext.is_null_value("n/a")
        assert not wikitext.is_null_value("Deceased")


class TestPreprocess:
    def test_removes_comments_refs_and_tables(self) -> None:
        markup = "a<!--hide-->b<ref>cite</ref>c\n{|\n|junk\n|}\nd"
        cleaned = wikitext.preprocess(markup)
        assert "hide" not in cleaned
        assert "cite" not in cleaned
        assert "junk" not in cleaned
        assert "abc" in cleaned.replace("\n", "")
