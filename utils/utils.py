from PIL import Image
from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.image import preprocess_image, show_cam_on_image
from DataSet.ChestXRayImageDatasetClass import ChestXRayImageDataset
import matplotlib.pyplot as plt
from matplotlib import rcParams
import pandas as pd
import torch
import tensorflow as tf
import torch.nn as nn
from torchvision import datasets, models, transforms
import numpy as np
import cv2
from numpy import nan_to_num
from torchvision.transforms import Compose, Normalize, ToTensor

rcParams['figure.figsize'] = 50, 50

transform = transforms.Compose([
    transforms.Resize(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225])
])


dis_labels = ['Atelectasis', 'Cardiomegaly', 'Consolidation', 'Edema',
          'Effusion', 'Emphysema', 'Fibrosis', 'Hernia', 'Infiltration',
          'Mass', 'Nodule', 'Pleural_Thickening', 'Pneumonia', 'Pneumothorax', 'none']


def get_model(num_classes):
    model_ = models.resnet50(pretrained=True, progress=True)
    # change the last linear layer
    num_ftrs = model_.fc.in_features
    model_.fc = nn.Linear(num_ftrs, num_classes)
    return model_


model = get_model(15)
model.load_state_dict(torch.load('saved_model/model_weights.pth', map_location=torch.device('cpu')))


def get_all_preds(model, loader):
    all_preds = torch.tensor([])
    for batch in loader:
        images, labels = batch

        preds = model(images)
        all_preds = torch.cat(
            (all_preds, preds),
            dim=0
        )
    return tf.nn.sigmoid(all_preds)


def plot_pred(values, filename):
    plt.close('all')
    top3 = sorted(range(len(values)), key=lambda i: values[i])[-3:]
    color = []
    for i in range(15):
        if i in top3:
            color.append('red')
        else:
            color.append('blue')
    plt.bar(dis_labels, values, color=color)
    plt.title('Model predictions', fontsize=50)
    plt.xticks(rotation=90, fontsize=50)
    plt.yticks(fontsize=50)
    plt.savefig(f'cam_pred/plot_{filename}')
    plt.close()


def predict(filename):
    df = pd.DataFrame.from_dict({'idx': [f'{filename}'], 'findings': ['none']})
    data = ChestXRayImageDataset('', df, transform=transform)
    loader = torch.utils.data.DataLoader(data, batch_size=64)

    with torch.no_grad():
        train_preds = get_all_preds(model, loader)

    pred_list = train_preds.numpy().tolist()[0]

    rgb_img = cv2.imread(f'static/{filename}', 1)[:, :, ::-1]
    rgb_img = cv2.resize(rgb_img, (224, 224))
    rgb_img = np.float32(rgb_img) / 255
    input_tensor = preprocess_image(rgb_img, mean=[0.485, 0.456, 0.406],
                                    std=[0.229, 0.224, 0.225])
    target_layer = model.layer4[-1]
    cam_gc = GradCAM(model=model, target_layer=target_layer, use_cuda=False)
    target_category = None
    grayscale_cam_gc = cam_gc(input_tensor=input_tensor, target_category=target_category)
    grayscale_cam_gc = grayscale_cam_gc[0,:]
    vis_gradcam = show_cam_on_image(rgb_img, grayscale_cam_gc)
    cv2.imwrite(f'cam_pred/heat_{filename}', vis_gradcam)
    return pred_list


def together(file):
    layer1 = Image.open(f'cam_pred/heat_{file}')
    layer2 = Image.open(f'cam_pred/plot_{file}')

    layer1 = layer1.resize((650, 650), Image.ANTIALIAS)
    layer2 = layer2.resize((650, 650), Image.ANTIALIAS)

    fs = [layer1, layer2]
    ncol = 2
    nrow = 1
    x, y = fs[1].size
    cvs = Image.new('RGB', (x * ncol, y * nrow))

    for i in range(len(fs)):
        px, py = x * int(i / nrow), y * (i % nrow)
        cvs.paste(fs[i], (px, py))

    cvs.save(f'cam_pred/together_{file}')


def top4(values, filename):
    print(filename)
    top4 = sorted(range(len(values)), key=lambda i: values[i])[-4:]
    print(top4)
    for i, elem in enumerate(top4):
        rgb_img = cv2.imread(f'static/{filename}', 1)[:, :, ::-1]
        rgb_img = cv2.resize(rgb_img, (224, 224))
        rgb_img = np.float32(rgb_img) / 255
        input_tensor = preprocess_image(rgb_img, mean=[0.485, 0.456, 0.406],
                                        std=[0.229, 0.224, 0.225])
        target_layer = model.layer4[-1]
        cam_gc = GradCAM(model=model, target_layer=target_layer, use_cuda=False)
        target_category = elem
        grayscale_cam_gc = cam_gc(input_tensor=input_tensor, target_category=target_category)
        grayscale_cam_gc = grayscale_cam_gc[0, :]
        vis_gradcam = show_cam_on_image(rgb_img, grayscale_cam_gc)
        position = (10, 10)
        cv2.putText(vis_gradcam,  # numpy array on which text is written
            f"{dis_labels[elem]}",  # text
            position,  # position at which writing has to start
            cv2.FONT_HERSHEY_SIMPLEX,  # font family
            0.75,  # font size
            (209, 80, 0, 255),  # font color
            1)
        cv2.imwrite(f'top4/heat{i}_{filename}', vis_gradcam)


    layer1 = Image.open(f'top4/heat0_{filename}').resize((325, 325), Image.ANTIALIAS)
    layer2 = Image.open(f'top4/heat1_{filename}').resize((325, 325), Image.ANTIALIAS)
    layer3 = Image.open(f'top4/heat2_{filename}').resize((325, 325), Image.ANTIALIAS)
    layer4 = Image.open(f'top4/heat3_{filename}').resize((325, 325), Image.ANTIALIAS)

    fs = [layer1, layer2, layer3, layer4]
    ncol = 2
    nrow = 2
    x, y = fs[1].size
    cvs = Image.new('RGB', (x * ncol, y * nrow))

    for i in range(len(fs)):
        px, py = x * int(i / nrow), y * (i % nrow)
        cvs.paste(fs[i], (px, py))

    cvs.save(f'cam_pred/together_{filename}')



