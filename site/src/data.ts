export interface Item {
  slug: string;
  name: string;
  emoji: string;
  season: string;
  description: string;
  nutrients: string[];
}

export interface Subgroup {
  id: string;
  name: string;
  items: Item[];
}

export interface Group {
  id: 'fruits' | 'vegetables';
  name: string;
  subgroups: Subgroup[];
}

const i = (
  slug: string, name: string, emoji: string, season: string,
  description: string, nutrients: string[],
): Item => ({ slug, name, emoji, season, description, nutrients });

export const groups: Group[] = [
  {
    id: 'fruits',
    name: 'Fruits',
    subgroups: [
      { id: 'citrus', name: 'Citrus', items: [
        i('orange', 'Orange', '🍊', 'Winter', 'A sweet, juicy citrus fruit, popular fresh or as juice.', ['Vitamin C', 'Folate', 'Fiber']),
        i('lemon', 'Lemon', '🍋', 'Year-round', 'A sour citrus used for flavoring drinks, dishes and desserts.', ['Vitamin C', 'Potassium']),
        i('lime', 'Lime', '🍈', 'Year-round', 'A small, tart green citrus common in cocktails and cooking.', ['Vitamin C', 'Antioxidants']),
        i('grapefruit', 'Grapefruit', '🍊', 'Winter', 'A tangy-bitter citrus with pink, red or white flesh.', ['Vitamin C', 'Vitamin A', 'Fiber']),
      ]},
      { id: 'berries', name: 'Berries', items: [
        i('strawberry', 'Strawberry', '🍓', 'Spring–Summer', 'A bright red, fragrant berry with seeds on the outside.', ['Vitamin C', 'Manganese', 'Folate']),
        i('blueberry', 'Blueberry', '🫐', 'Summer', 'Small blue berries rich in antioxidants.', ['Vitamin K', 'Vitamin C', 'Anthocyanins']),
        i('raspberry', 'Raspberry', '🍇', 'Summer', 'A delicate, tart-sweet berry made of tiny drupelets.', ['Fiber', 'Vitamin C', 'Manganese']),
        i('blackberry', 'Blackberry', '🫐', 'Summer', 'A dark, juicy berry growing on thorny canes.', ['Vitamin K', 'Fiber', 'Vitamin C']),
      ]},
      { id: 'pome', name: 'Pome fruits', items: [
        i('apple', 'Apple', '🍎', 'Autumn', 'A crisp, versatile fruit available in thousands of varieties.', ['Fiber', 'Vitamin C', 'Potassium']),
        i('pear', 'Pear', '🍐', 'Autumn', 'A soft, sweet fruit with a distinctive bell shape.', ['Fiber', 'Vitamin K', 'Copper']),
      ]},
      { id: 'stone', name: 'Stone fruits', items: [
        i('peach', 'Peach', '🍑', 'Summer', 'A fuzzy-skinned fruit with soft, juicy flesh.', ['Vitamin A', 'Vitamin C']),
        i('cherry', 'Cherry', '🍒', 'Summer', 'A small round stone fruit, sweet or sour.', ['Vitamin C', 'Potassium', 'Melatonin']),
        i('plum', 'Plum', '🍑', 'Summer', 'A juicy fruit that dries into prunes.', ['Vitamin C', 'Vitamin K']),
        i('apricot', 'Apricot', '🍑', 'Early summer', 'A small golden-orange fruit with velvety skin.', ['Vitamin A', 'Vitamin C', 'Fiber']),
      ]},
      { id: 'tropical', name: 'Tropical', items: [
        i('banana', 'Banana', '🍌', 'Year-round', 'A soft, sweet fruit that is a great source of energy.', ['Potassium', 'Vitamin B6', 'Fiber']),
        i('pineapple', 'Pineapple', '🍍', 'Spring–Summer', 'A tangy tropical fruit containing the enzyme bromelain.', ['Vitamin C', 'Manganese']),
        i('mango', 'Mango', '🥭', 'Summer', 'A fragrant, sweet fruit with a large central stone.', ['Vitamin C', 'Vitamin A', 'Folate']),
        i('kiwi', 'Kiwi', '🥝', 'Winter', 'A fuzzy brown fruit with tart green flesh.', ['Vitamin C', 'Vitamin K', 'Fiber']),
      ]},
    ],
  },
  {
    id: 'vegetables',
    name: 'Vegetables',
    subgroups: [
      { id: 'root', name: 'Root vegetables', items: [
        i('carrot', 'Carrot', '🥕', 'Year-round', 'A crunchy orange root, sweet when raw or cooked.', ['Vitamin A', 'Vitamin K', 'Fiber']),
        i('potato', 'Potato', '🥔', 'Autumn', 'A starchy tuber, a staple food around the world.', ['Potassium', 'Vitamin C', 'Vitamin B6']),
        i('beetroot', 'Beetroot', '🟣', 'Summer–Autumn', 'A deep-red earthy root, eaten roasted, pickled or raw.', ['Folate', 'Manganese', 'Nitrates']),
        i('radish', 'Radish', '🌱', 'Spring', 'A peppery, crunchy root usually eaten raw.', ['Vitamin C', 'Potassium']),
      ]},
      { id: 'leafy', name: 'Leafy greens', items: [
        i('spinach', 'Spinach', '🥬', 'Spring', 'Tender dark leaves, eaten raw or cooked.', ['Iron', 'Vitamin K', 'Folate']),
        i('lettuce', 'Lettuce', '🥬', 'Spring–Summer', 'A mild, crisp leaf and the base of most salads.', ['Vitamin K', 'Vitamin A']),
        i('kale', 'Kale', '🥬', 'Winter', 'A hardy, curly leaf green that is very nutrient-dense.', ['Vitamin K', 'Vitamin C', 'Vitamin A']),
      ]},
      { id: 'cruciferous', name: 'Cruciferous', items: [
        i('broccoli', 'Broccoli', '🥦', 'Autumn', 'Green flower heads on thick stalks.', ['Vitamin C', 'Vitamin K', 'Fiber']),
        i('cauliflower', 'Cauliflower', '🥦', 'Autumn', 'A pale, dense flower head, great roasted or riced.', ['Vitamin C', 'Choline']),
        i('cabbage', 'Cabbage', '🥬', 'Autumn–Winter', 'Layered leaves forming a dense head; used fresh or fermented.', ['Vitamin K', 'Vitamin C']),
      ]},
      { id: 'alliums', name: 'Alliums', items: [
        i('onion', 'Onion', '🧅', 'Year-round', 'A pungent bulb that sweetens when cooked.', ['Vitamin C', 'Quercetin']),
        i('garlic', 'Garlic', '🧄', 'Summer', 'A strongly flavored bulb made of cloves.', ['Manganese', 'Vitamin B6', 'Allicin']),
        i('leek', 'Leek', '🌱', 'Autumn–Winter', 'A mild, sweet relative of the onion with long stalks.', ['Vitamin K', 'Vitamin A']),
      ]},
      { id: 'fruiting', name: 'Fruiting vegetables', items: [
        i('tomato', 'Tomato', '🍅', 'Summer', 'Botanically a fruit; juicy and savory.', ['Vitamin C', 'Lycopene', 'Potassium']),
        i('cucumber', 'Cucumber', '🥒', 'Summer', 'A cool, watery vegetable, often eaten raw.', ['Vitamin K', 'Water']),
        i('bell-pepper', 'Bell pepper', '🫑', 'Summer', 'A sweet, crunchy pepper in many colors.', ['Vitamin C', 'Vitamin A']),
        i('eggplant', 'Eggplant', '🍆', 'Summer', 'A spongy purple vegetable that absorbs flavors.', ['Fiber', 'Manganese']),
        i('zucchini', 'Zucchini', '🥒', 'Summer', 'A tender summer squash.', ['Vitamin C', 'Potassium']),
      ]},
    ],
  },
];

export const allItems = groups.flatMap((g) =>
  g.subgroups.flatMap((s) =>
    s.items.map((it) => ({ ...it, groupId: g.id, subgroupId: s.id, groupName: g.name })),
  ),
);

export const findItem = (slug: string) => allItems.find((x) => x.slug === slug);
