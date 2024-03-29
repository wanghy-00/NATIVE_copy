import torch
import mmkgc
from mmkgc.config import Tester, AdvMixTrainer, WCGTrainerDB15KGP
from mmkgc.module.model import AdvMixRotatE, AdvRelRotatEDB15K
from mmkgc.module.loss import SigmoidLoss
from mmkgc.module.strategy import NegativeSamplingGP
from mmkgc.data import TrainDataLoader, TestDataLoader
from mmkgc.adv.modules import MultiGenerator, CombinedGenerator3

from args import get_args

if __name__ == "__main__":
    args = get_args()
    print(args)
    # set the seed
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    # dataloader for training
    train_dataloader = TrainDataLoader(
        in_path="./benchmarks/" + args.dataset + '/',
        batch_size=args.batch_size,
        threads=8,
        sampling_mode="normal",
        bern_flag=1,
        filter_flag=1,
        neg_ent=args.neg_num,
        neg_rel=0
    )
    # dataloader for test
    test_dataloader = TestDataLoader(
        "./benchmarks/" + args.dataset + '/', "link")
    img_emb = torch.load('./embeddings/' + args.dataset + '-visual.pth')
    text_emb = torch.load('./embeddings/' + args.dataset + '-textual.pth')
    num_emb = torch.load('./embeddings/' + args.dataset + '-numeric.pth')
    # define the model
    kge_score = AdvRelRotatEDB15K(
        ent_tot=train_dataloader.get_ent_tot(),
        rel_tot=train_dataloader.get_rel_tot(),
        dim=args.dim,
        margin=args.margin,
        epsilon=2.0,
        img_emb=img_emb,
        text_emb=text_emb,
        numeric_emb=num_emb,
    )
    print(kge_score)
    # define the loss function
    model = NegativeSamplingGP(
        model=kge_score,
        loss=SigmoidLoss(adv_temperature=args.adv_temp),
        batch_size=train_dataloader.get_batch_size(),
    )
    
    adv_generator = CombinedGenerator3(
        noise_dim=64,
        structure_dim=2*args.dim,
        img_dim=3*args.dim
    )
    # train the model
    trainer = WCGTrainerDB15KGP(
        model=model,
        data_loader=train_dataloader,
        train_times=args.epoch,
        alpha=args.learning_rate,
        use_gpu=True,
        opt_method='Adam',
        generator=adv_generator,
        lrg=args.lrg,
        mu=args.mu
    )

    trainer.run()
    kge_score.save_checkpoint(args.save)

    # test the model
    # kge_score.load_checkpoint(args.save)
    tester = Tester(model=kge_score, data_loader=test_dataloader, use_gpu=True)
    tester.run_link_prediction(type_constrain=False)
