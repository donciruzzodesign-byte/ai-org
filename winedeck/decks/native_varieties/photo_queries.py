# -*- coding: utf-8 -*-
"""各品種カード用のPexels検索クエリ（grape, local, jp）。generate.pyのREGIONS順と一致させる。"""

QUERIES = {
"valle-daosta": [
    ("red wine grapes vineyard alps", "fontina cheese fondue", "teriyaki chicken"),
    ("white wine grapes vineyard mountain", "alpine cheese fondue", "cold tofu japanese"),
],
"piemonte": [
    ("red wine grapes vineyard piedmont", "beef stew braised red wine", "japanese sukiyaki hot pot"),  # barbera (reuse sample)
    ("white wine grapes vineyard italy", "italian antipasto platter", "tempura white fish"),
    ("red wine grapes close up", "italian appetizer platter", "grilled chicken skewers yakitori"),
    ("red wine grapes vineyard hills", "italian pasta meat sauce", "mapo tofu"),
],
"liguria": [
    ("white wine grapes vineyard coast", "fried seafood italian", "grilled fish salt"),
    ("red wine grapes vineyard", "rabbit stew", "yakitori salt skewers"),
    ("white wine grapes vineyard cinque terre", "anchovy appetizer", "whitebait rice bowl"),
],
"lombardia": [
    ("red wine grapes vineyard lake", "duck ragu pasta", "unagi grilled eel"),
    ("white wine grapes vineyard lake garda", "seafood risotto", "japanese egg custard chawanmushi"),
    ("muscat grapes vineyard", "gorgonzola cheese", "japanese chestnut sweets"),
],
"trentino-alto-adige": [
    ("red wine grapes vineyard mountains", "polenta meat stew", "sukiyaki beef"),
    ("red wine grapes vineyard", "speck ham sauerkraut", "unagi grilled eel"),
    ("white wine grapes vineyard", "tyrolean dumplings", "japanese egg custard chawanmushi"),
    ("red wine grapes vineyard alps", "cured ham cheese platter", "shabu shabu"),
],
"veneto": [
    ("white wine grapes vineyard soave", "salt cod stew", "japanese rolled omelette dashimaki"),
    ("red wine grapes vineyard valpolicella", "braised beef stew italian", "miso grilled beef"),
    ("red wine grapes vineyard", "beans pasta soup italian", "beef tendon stew"),
],
"friuli-venezia-giulia": [
    ("white wine grapes vineyard", "prosciutto cheese platter", "cold tofu japanese"),
    ("red wine grapes vineyard", "sausage sauerkraut", "ginger pork grilled"),
    ("white wine grapes vineyard hills", "cheese platter prosciutto", "japanese vinegared cucumber"),
],
"emilia-romagna": [
    ("red wine grapes vineyard", "lasagna bolognese", "japanese fried chicken karaage"),
    ("white wine grapes vineyard", "piadina flatbread cheese", "tofu salad japanese"),
],
"toscana": [
    ("red wine grapes vineyard tuscany", "florentine steak", "grilled beef tongue"),
    ("white wine grapes vineyard tuscany", "tuscan bread soup", "tempura vegetables"),
    ("red wine grapes vineyard tuscany hills", "italian sausage beans", "simmered vegetables japanese"),
    ("white wine grapes vineyard coast", "seafood soup italian", "steamed clams sake"),
],
"umbria": [
    ("red wine grapes vineyard hills", "pasta wild boar ragu", "beef miso stew"),
    ("white wine grapes vineyard", "bruschetta olive oil", "edamame"),
    ("white wine grapes vineyard italy", "truffle egg dish", "japanese rolled omelette"),
],
"marche": [
    ("white wine grapes vineyard hills", "italian seafood soup", "sushi white fish"),
    ("red wine grapes vineyard", "italian lasagna layered pasta", "braised pork belly"),
    ("red sparkling wine grapes vineyard", "italian meatballs tomato", "japanese fried chicken"),
],
"lazio": [
    ("red wine grapes vineyard rome", "roast lamb", "grilled lamb skewers"),
    ("white wine grapes vineyard", "roman artichoke", "tempura wild vegetables"),
],
"abruzzo": [
    ("red wine grapes vineyard hills", "lamb skewers grill", "grilled beef bbq"),
    ("white wine grapes vineyard", "pecorino cheese plate", "japanese citrus chicken"),
    ("white wine grapes vineyard", "clam pasta italian", "clams sake steamed"),
],
"molise": [
    ("red wine grapes vineyard hills", "lamb grill", "beef offal stew"),
],
"campania": [
    ("red wine grapes vineyard volcano", "italian beef ragu pasta", "sukiyaki beef"),
    ("white wine grapes vineyard volcanic", "buffalo mozzarella", "sea bream carpaccio"),
    ("white wine grapes vineyard", "mozzarella seafood risotto", "japanese egg custard chawanmushi"),
    ("white wine grapes vineyard", "fried seafood pizza italian", "tempura white fish"),
],
"puglia": [
    ("red wine grapes vineyard", "grilled pork roll italian", "japanese wagyu bbq"),
    ("red wine grapes vineyard", "orecchiette pasta meat sauce", "grilled chicken liver skewers"),
    ("rose wine grapes vineyard", "octopus salad", "grilled sea bream"),
    ("red wine grapes vineyard", "lamb grill italian", "grilled beef yakiniku"),
],
"basilicata": [
    ("red wine grapes vineyard volcano", "pasta beans italian", "charcoal grilled beef"),
    ("muscat grapes vineyard", "italian almond pastry", "japanese peach compote"),
],
"calabria": [
    ("red wine grapes vineyard calabria", "spicy sausage nduja", "spicy miso hotpot"),
    ("white wine grapes drying raisin", "almond pastry italian", "japanese dried persimmon"),
],
"sicilia": [
    ("red wine grapes vineyard sicily", "pasta eggplant sicilian", "simmered eggplant japanese"),
    ("red wine grapes vineyard etna volcano", "rabbit stew italian", "japanese chicken hot pot"),
    ("white wine grapes vineyard sicily", "seafood couscous", "sardine plum simmered"),
    ("white wine grapes vineyard sicily", "italian bread olive oil", "cold tofu shiso"),
],
"sardegna": [
    ("white wine grapes vineyard sardinia", "bottarga pasta", "clam soup japanese"),
    ("red wine grapes vineyard sardinia", "roast suckling pig", "braised pork belly"),
    ("red wine grapes old vines vineyard", "sardinian pasta sausage sauce", "braised pork miso"),
    ("white wine grapes vineyard", "bottarga salad", "cold somen noodles"),
],
}
