# Use an official Python runtime as a parent image
FROM python:3.10
RUN apt-get update && apt-get install -y nano
# Set the working directory in the container
WORKDIR /app
COPY . /app
COPY ./.env /app/.env
# Make the script executable
RUN chmod +x /app/install_inkbytes_libraries.sh

# Install any needed packages specified in requirements.txt
# If you have a requirements.txt, uncomment the next line
# COPY requirements.txt /app/
RUN rm -iRf /app/venv
RUN python3 -m venv /app/venv


RUN /app/install_inkbytes_libraries.sh https://gitlab.com/inkbytes/common.git develop inkbytes
RUN /app/install_inkbytes_libraries.sh https://gitlab.com/inkbytes/models.git develop inkbytes
RUN /app/install_inkbytes_libraries.sh https://gitlab.com/inkbytes/database.git develop inkbytes
RUN mkdir ../Storage
COPY ./requirements.txt /app/
RUN /app/venv/bin/pip install --upgrade pip
RUN /app/venv/bin/pip install -r /app/requirements.txt
RUN /app/venv/bin/pip install pytz nltk
RUN echo "source /app/venv/bin/activate" > /app/activate_venv.sh
RUN chmod +x /app/activate_venv.sh
RUN echo "source /app/activate_venv.sh" >> /root/.bashrc
# Run the application.
EXPOSE 8585
#CMD ["source", "venv/bin/activate"]
#ENTRYPOINT ["/bin/bash"]