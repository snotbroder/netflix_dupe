const showButtons = document.querySelectorAll(".openDialogBtn");

showButtons.forEach(button => {
  button.addEventListener("click", () => {
    // get the user_pk
    const userPk = button.dataset.user; 
    const dialog = document.getElementById(`dialog-${userPk}`);
    if (dialog) dialog.showModal();
  });
});


const closeButtons = document.querySelectorAll(".closeDialogBtn");

closeButtons.forEach(button => {
  button.addEventListener("click", () => {
    const dialog = button.closest("dialog");
    if (dialog) dialog.close();
  });
});
