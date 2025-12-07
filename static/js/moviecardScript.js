const cards = document.querySelectorAll('.card-container');

cards.forEach(card => {
  card.addEventListener('mouseover', () => {
    // Remove .card-active from all cards
    cards.forEach(c => c.classList.remove('card-active'));

    // Add .card-active to the hovered card
    card.classList.add('card-active');
    // console.log("added class")
});

// Remove class from the active card
card.addEventListener('mouseout', () => {
    card.classList.remove('card-active');
    // console.log("removed class")
  });
});