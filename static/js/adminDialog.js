const dialog = document.querySelector("dialog");
const showButtons = document.querySelectorAll(".openDialog");
const closeButton = document.querySelector("#closeDialog");

// "Show the dialog" button opens the dialog modally
showButtons.forEach(button => {
  button.addEventListener("click", () => {
    dialog.showModal();
  });
});

// "Close" button closes the dialog
closeButton.addEventListener("click", () => {
  dialog.close();
});