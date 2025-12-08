const cards = document.querySelectorAll('.card-container');

cards.forEach(card => {
  card.addEventListener('mouseover', () => {
    // remove .card-active from all cards
    cards.forEach(c => c.classList.remove('card-active'));

    // add .card-active to the hovered card
    card.classList.add('card-active');
});

// remove class from the active card
card.addEventListener('mouseout', () => {
    card.classList.remove('card-active');
  });
});