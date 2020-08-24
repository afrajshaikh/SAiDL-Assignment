# -*- coding: utf-8 -*-
"""partcRandomCrop.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1MPIA43l6F-AfiEK7yTlgPcnEnfrpRp16
"""

# Commented out IPython magic to ensure Python compatibility.
# %matplotlib inline

import torch
import torchvision
import torchvision.transforms as transforms
import torchvision.datasets as dsets
from torch.autograd import Variable
import torch.nn as nn
import matplotlib.pyplot as plt
import numpy as np

train_dataset = dsets.CIFAR10(root='./data' , train=True, transform=transforms.Compose([transforms.RandomCrop(32),transforms.ToTensor(),transforms.Normalize((0.5,0.5,0.5),(0.5,0.5,0.5))]), download=True)
test_dataset = dsets.CIFAR10(root='./data' , train=False, transform=transforms.Compose([transforms.RandomCrop(32),transforms.ToTensor(),transforms.Normalize((0.5,0.5,0.5),(0.5,0.5,0.5))]), download=False)



batch_size=64
n_iters=10000
num_epochs= n_iters/(len(train_dataset)/batch_size)
num_epochs = int(num_epochs)

train_loader = torch.utils.data.DataLoader(dataset = train_dataset, batch_size=batch_size, shuffle = True)

test_loader = torch.utils.data.DataLoader(dataset = test_dataset, batch_size=batch_size, shuffle = False)

batch = next(iter(train_loader))

images , labels = batch
print(images.shape)
grid = torchvision.utils.make_grid(images, nrow =8)
plt.figure(figsize = (15,15))
plt.imshow(np.transpose(grid, (1,2,0)))

class LeNet(nn.Module):
  def __init__(self):
    super(LeNet,self).__init__()
    self.relu = nn.ReLU()
    self.avg_pool = nn.AvgPool2d(2, 2)


    self.conv1 = nn.Conv2d(3 ,6 ,5)     # input channels changed from 3 to 1
    self.conv2 = nn.Conv2d(6 ,16 ,5)
    self.conv3 = nn.Conv2d(16, 120,5)
    self.fc1 = nn.Linear(120 ,84)
    self.fc2 = nn.Linear(84, 10)
  def forward(self,x):
    x = self.relu(self.conv1(x))
    x = self.avg_pool(x)
    x = self.relu(self.conv2(x))
    x = self.avg_pool(x)
    x = self.relu(self.conv3(x))

    x = x.reshape(x.shape[0],-1)
    x = self.relu(self.fc1(x))
    x = self.fc2(x)
    return x

model = LeNet()

criterion = nn.CrossEntropyLoss()

learning_rate = 0.01
optimizer = torch.optim.SGD(model.parameters(), lr = learning_rate, momentum=0.9)



iter =0
for epoch in range(num_epochs):
  running_loss=0.0
  for i, data in enumerate(train_loader,0):
    input, labels = data

    optimizer.zero_grad()
    outputs = model(input)

    loss = criterion(outputs,labels)
    loss.backward()
    optimizer.step()

    running_loss=loss.item()
    if i % 500 == 0:
      print('[%d, %5d] loss: %.3f' %
                  (epoch + 1, i + 1, running_loss))
      running_loss = 0.0

print('Finished Training')

correct = 0
total = 0
with torch.no_grad():
    for data in test_loader:
        images, labels = data
        outputs = model(images)
        _, predicted = torch.max(outputs.data, 1)
        total += labels.size(0)
        correct += (predicted == labels).sum().item()

print('Accuracy of the network on the 10000 test images: %d %%' % (
    100 * correct / total))