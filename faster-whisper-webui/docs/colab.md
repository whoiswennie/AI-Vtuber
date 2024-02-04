# Running Whisper on Google Colab

If you don't have a decent GPU or any experience in running command-line applications, you might want to try this Google Colab instead:

* [Google Colab - Whisper WebUI GPU](https://colab.research.google.com/drive/1qeTSvi7Bt_5RMm88ipW4fkcsMOKlDDss?usp=sharing)
* [Screenshots](https://imgur.com/a/ZfY6uBO)

The runtime (Runtime -> Change runtime type -> Hardware accelerator) should already be set top GPU. But if not, change it to GPU.

Then, sign in to Google if you haven't already. Next, click on "Connect" at the top right.

Under "Checking out WebUI from Git", click on the [play icon](https://imgur.com/a/81gOLyD) that appears in "[ ]" at the left. If you get a warning, click "Run anyway".

After this step has completed, it should be get a green check mark. Then move on to the next section under "Installing dependencies", and click in "[ ]" again. This might take approximately 30 seconds.

Once this has completed, scroll down to the "Run WebUI" section, and click on "[ ]". This will launch the WebUI in a shared link (expires in 72 hours). To open the UI, click on the link next to "Running on public URL", which will be something like https://12xxx.gradio.app/

The audio length in this version is not restricted, and it will run much faster as it is backed by a GPU. You can also run it using the "Large" model. Also note that it might take some time to start the model the first time, as it may need to download a 2.8 GB file on Google's servers.

Once you're done, you can close the WebUI session by clicking the animated close button under "Run WebUI". You can also do this if you encounter any errors and need to restart the UI. You should also go to "Manage Sessions" and terminate the session, otherwise you may end up using all your free compute credits.