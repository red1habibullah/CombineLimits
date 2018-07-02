import logging

from array import array

import ROOT
from CombineLimits.Limits.utilities import *
class Model(object):

    def __init__(self,name,**kwargs):
        self.name = name
        self.x = kwargs.pop('x','x')
        self.y = kwargs.pop('y','y')
        self.z = kwargs.pop('z','z')
        self.kwargs = kwargs

    def wsimport(self, ws, *args) :
        # getattr since import is special in python
        # NB RooWorkspace clones object
        if len(args) < 2 :
            # Useless RooCmdArg: https://sft.its.cern.ch/jira/browse/ROOT-6785
            args += (ROOT.RooCmdArg(),)
        return getattr(ws, 'import')(*args)

    def update(self,**kwargs):
        '''Update the floating parameters'''
        self.kwargs.update(kwargs)

    def build(self,ws,label):
        '''Dummy method to add model to workspace'''
        logging.debug('Building {}'.format(label))

    def fit(self,ws,hist,name,save=False,doErrors=False,saveDir=''):
        '''Fit the model to a histogram and return the fit values'''

        if isinstance(hist,ROOT.TH1):
            dhname = 'dh_{0}'.format(name)
            hist = ROOT.RooDataHist(dhname, dhname, ROOT.RooArgList(ws.var(self.x)), hist)
        self.build(ws,name)
        model = ws.pdf(name)
        fr = model.fitTo(hist,ROOT.RooFit.Save(),ROOT.RooFit.SumW2Error(True))
        pars = fr.floatParsFinal()
        vals = {}
        errs = {}
        for p in range(pars.getSize()):
            vals[pars.at(p).GetName()] = pars.at(p).getValV()
            errs[pars.at(p).GetName()] = pars.at(p).getError()

        if save:
            if saveDir: python_mkdir(saveDir)
            savename = '{}/{}_{}'.format(saveDir,self.name,name) if saveDir else '{}_{}'.format(self.name,name)
            x = ws.var(self.x)
            xFrame = x.frame()
            xFrame.SetTitle('')
            hist.plotOn(xFrame)
            model.plotOn(xFrame)
            model.paramOn(xFrame,ROOT.RooFit.Layout(0.72,0.98,0.90))
            canvas = ROOT.TCanvas(savename,savename,800,800)
            canvas.SetRightMargin(0.3)
            xFrame.Draw()
            prims = canvas.GetListOfPrimitives()
            for prim in prims:
                if 'paramBox' in prim.GetName():
                    prim.SetTextSize(0.02)
            canvas.Print('{0}.png'.format(savename))

        if doErrors:
            return vals, errs
        return vals

    def fit2D(self,ws,hist,name,save=False,doErrors=False,saveDir=''):
        '''Fit the model to a histogram and return the fit values'''

        if isinstance(hist,ROOT.TH1):
            dhname = 'dh_{0}'.format(name)
            hist = ROOT.RooDataHist(dhname, dhname, ROOT.RooArgList(ws.var(self.x),ws.var(self.y)), hist)
        self.build(ws,name)
        model = ws.pdf(name)
        fr = model.fitTo(hist,ROOT.RooFit.Save(),ROOT.RooFit.SumW2Error(True))
        pars = fr.floatParsFinal()
        vals = {}
        errs = {}
        for p in range(pars.getSize()):
            vals[pars.at(p).GetName()] = pars.at(p).getValV()
            errs[pars.at(p).GetName()] = pars.at(p).getError()

        if save:
            if saveDir: python_mkdir(saveDir)
            savename = '{}/{}_{}'.format(saveDir,self.name,name) if saveDir else '{}_{}'.format(self.name,name)
            x = ws.var(self.x)
            xFrame = x.frame()
            xFrame.SetTitle('')
            hist.plotOn(xFrame)
            model.plotOn(xFrame)
            model.paramOn(xFrame,ROOT.RooFit.Layout(0.72,0.98,0.90))
            canvas = ROOT.TCanvas(savename,savename,800,800)
            canvas.SetRightMargin(0.3)
            xFrame.Draw()
            prims = canvas.GetListOfPrimitives()
            for prim in prims:
                if 'paramBox' in prim.GetName():
                    prim.SetTextSize(0.02)
            canvas.Print('{0}_xproj.png'.format(savename))

            y = ws.var(self.y)
            yFrame = y.frame()
            yFrame.SetTitle('')
            hist.plotOn(yFrame)
            model.plotOn(yFrame)
            model.paramOn(yFrame,ROOT.RooFit.Layout(0.72,0.98,0.90))
            yFrame.Draw()
            prims = canvas.GetListOfPrimitives()
            for prim in prims:
                if 'paramBox' in prim.GetName():
                    prim.SetTextSize(0.02)
            canvas.Print('{0}_yproj.png'.format(savename))

            histM = model.createHistogram('x,y',100,100)
            histM.SetLineColor(ROOT.kBlue)
            histM.Draw('surf')
            canvas.Print('{0}_model.png'.format(savename))

            if isinstance(hist,ROOT.RooDataSet):
                histD = hist.createHistogram(x,y,20,20,'1','{}_hist'.format(savename))
                histD.SetLineColor(ROOT.kBlack)
                histD.Draw('surf')
                canvas.Print('{0}_dataset.png'.format(savename))


        if doErrors:
            return vals, errs
        return vals

    def setIntegral(self,integral):
        self.integral = integral

    def getIntegral(self):
        if hasattr(self,'integral'): return self.integral
        return 1

class ModelSpline(Model):

    def __init__(self,name,**kwargs):
        self.MH = kwargs.pop('MH','MH')
        super(ModelSpline,self).__init__(name,**kwargs)

    def setIntegral(self,masses,integrals):
        self.masses = masses
        self.integrals = integrals

    def buildIntegral(self,ws,label):
        if not hasattr(self,'integrals'): return 
        integralSpline  = ROOT.RooSpline1D(label,  label,  ws.var(self.MH), len(self.masses), array('d',self.masses), array('d',self.integrals))
        # import to workspace
        getattr(ws, "import")(integralSpline, ROOT.RooFit.RecycleConflictNodes())

class SplineParam(object):

    def __init__(self,name,**kwargs):
        self.name = name
        self.kwargs = kwargs

    def build(self,ws,label):
        logging.debug('Building {}'.format(label))
        paramName = '{0}'.format(label) 
        ws.factory('{0}[0,-10,10]'.format(paramName))

class Spline(object):

    def __init__(self,name,**kwargs):
        self.name = name
        self.mh = kwargs.pop('MH','MH')
        self.kwargs = kwargs

    def build(self,ws,label):
        logging.debug('Building {}'.format(label))
        masses = self.kwargs.get('masses', [])
        values = self.kwargs.get('values', [])
        shifts = self.kwargs.get('shifts', {})
        splineName = label
        if shifts:
            centralName = '{0}_central'.format(label)
            splineCentral = ROOT.RooSpline1D(centralName,  centralName,  ws.var(self.mh), len(masses), array('d',masses), array('d',values))
            getattr(ws, "import")(splineCentral, ROOT.RooFit.RecycleConflictNodes())
            shiftFormula = '{0}'.format(centralName)
            for shift in shifts:
                up = [u-c for u,c in zip(shifts[shift]['up'],values)]
                down = [d-c for d,c in zip(shifts[shift]['down'],values)]
                upName = '{0}_{1}Up'.format(splineName,shift)
                downName = '{0}_{1}Down'.format(splineName,shift)
                splineUp   = ROOT.RooSpline1D(upName,  upName,  ws.var(self.mh), len(masses), array('d',masses), array('d',up))
                splineDown = ROOT.RooSpline1D(downName,downName,ws.var(self.mh), len(masses), array('d',masses), array('d',down))
                getattr(ws, "import")(splineUp, ROOT.RooFit.RecycleConflictNodes())
                getattr(ws, "import")(splineDown, ROOT.RooFit.RecycleConflictNodes())
                shiftFormula += ' + TMath::Max(0,{shift})*{upName} + TMath::Min(0,{shift})*{downName}'.format(shift=shift,upName=upName,downName=downName)
            spline = ROOT.RooFormulaVar(splineName, splineName, shiftFormula, ROOT.RooArgList())
        else:
            spline = ROOT.RooSpline1D(splineName,  splineName,  ws.var(self.mh), len(masses), array('d',masses), array('d',values))
        getattr(ws, "import")(spline, ROOT.RooFit.RecycleConflictNodes())

class Polynomial(Model):

    def __init__(self,name,**kwargs):
        super(Chebychev,self).__init__(name,**kwargs)

    def build(self,ws,label):
        logging.debug('Building {}'.format(label))
        order = self.kwargs.get('order',1)
        params = ['p{}_{}'.format(o,label) for o in range(order)]
        ranges = [self.kwargs.get('p{}'.format(o),[0,-1,1]) for o in range(order)]
        ws.factory('Polynomial::{}({}, {{ {} }})'.format(label, self.x, ', '.join(['{}[{}]'.format(p,','.join([str(r) for r in rs])) for p,rs in zip(params,ranges)])))
        self.params = params

class PolynomialSpline(ModelSpline):

    def __init__(self,name,**kwargs):
        super(ChebychevSpline,self).__init__(name,**kwargs)

    def build(self,ws,label):
        logging.debug('Building {}'.format(label))
        order = self.kwargs.get('order',1)
        masses = self.kwargs.get('masses',[])
        paramSplines = {}
        params = []
        for o in range(order):
            ps = self.kwargs.get('p{}'.format(o), [])
            paramName = 'p{}_{}'.format(o,label)
            paramSplines[o] = ROOT.RooSpline1D(paramName, paramName, ws.var('MH'), len(masses), array('d',masses), array('d',ps))
            getattr(ws, "import")(paramSplines[o], ROOT.RooFit.RecycleConflictNodes())
            params += [paramName]
        ws.factory('Polynomial::{}({}, {{ {} }})'.format(label, self.x, ', '.join(['{}[0, -10, 10]'.format(p) for p in params])))
        self.params = params

class Chebychev(Model):

    def __init__(self,name,**kwargs):
        super(Chebychev,self).__init__(name,**kwargs)

    def build(self,ws,label):
        logging.debug('Building {}'.format(label))
        order = self.kwargs.get('order',1)
        params = ['p{}_{}'.format(o,label) for o in range(order)]
        ranges = [self.kwargs.get('p{}'.format(o),[0,-1,1]) for o in range(order)]
        ws.factory('Chebychev::{}({}, {{ {} }})'.format(label, self.x, ', '.join(['{}[{}]'.format(p,','.join([str(r) for r in rs])) for p,rs in zip(params,ranges)])))
        self.params = params

class ChebychevSpline(ModelSpline):

    def __init__(self,name,**kwargs):
        super(ChebychevSpline,self).__init__(name,**kwargs)

    def build(self,ws,label):
        logging.debug('Building {}'.format(label))
        order = self.kwargs.get('order',1)
        masses = self.kwargs.get('masses',[])
        paramSplines = {}
        params = []
        for o in range(order):
            ps = self.kwargs.get('p{}'.format(o), [])
            paramName = 'p{}_{}'.format(o,label)
            paramSplines[o] = ROOT.RooSpline1D(paramName, paramName, ws.var('MH'), len(masses), array('d',masses), array('d',ps))
            getattr(ws, "import")(paramSplines[o], ROOT.RooFit.RecycleConflictNodes())
            params += [paramName]
        ws.factory('Chebychev::{}({}, {{ {} }})'.format(label, self.x, ', '.join(['{}[0, -10, 10]'.format(p) for p in params])))
        self.params = params

class Gaussian(Model):

    def __init__(self,name,**kwargs):
        super(Gaussian,self).__init__(name,**kwargs)

    def build(self,ws,label):
        logging.debug('Building {}'.format(label))
        meanName = 'mean_{0}'.format(label)
        sigmaName = 'sigma_{0}'.format(label)
        mean = self.kwargs.get('mean',[1,0,1000])
        sigma = self.kwargs.get('sigma',[1,0,100])
        # variables
        ws.factory('{0}[{1}, {2}, {3}]'.format(meanName,*mean))
        ws.factory('{0}[{1}, {2}, {3}]'.format(sigmaName,*sigma))
        # build model
        ws.factory("Gaussian::{0}({1}, {2}, {3})".format(label,self.x,meanName,sigmaName))
        self.params = [meanName,sigmaName]

class GaussianSpline(ModelSpline):

    def __init__(self,name,**kwargs):
        super(GaussianSpline,self).__init__(name,**kwargs)

    def build(self,ws,label):
        logging.debug('Building {}'.format(label))
        meanName = 'mean_{0}'.format(label)
        sigmaName = 'sigma_{0}'.format(label)
        masses = self.kwargs.get('masses', [])
        means  = self.kwargs.get('means',  [])
        sigmas = self.kwargs.get('sigmas', [])
        # splines
        meanSpline  = ROOT.RooSpline1D(meanName,  meanName,  ws.var('MH'), len(masses), array('d',masses), array('d',means))
        sigmaSpline = ROOT.RooSpline1D(sigmaName, sigmaName, ws.var('MH'), len(masses), array('d',masses), array('d',sigmas))
        # import
        getattr(ws, "import")(meanSpline, ROOT.RooFit.RecycleConflictNodes())
        getattr(ws, "import")(sigmaSpline, ROOT.RooFit.RecycleConflictNodes())
        # build model
        ws.factory("Gaussian::{0}({1}, {2}, {3})".format(label,self.x,meanName,sigmaName))
        self.params = [meanName,sigmaName]

class BreitWigner(Model):

    def __init__(self,name,**kwargs):
        super(BreitWigner,self).__init__(name,**kwargs)

    def build(self,ws,label):
        logging.debug('Building {}'.format(label))
        meanName = 'mean_{0}'.format(label)
        widthName = 'width_{0}'.format(label)
        mean  = self.kwargs.get('mean',  [1,0,1000])
        width = self.kwargs.get('width', [1,0,100])
        # variables
        ws.factory('{0}[{1}, {2}, {3}]'.format(meanName,*mean))
        ws.factory('{0}[{1}, {2}, {3}]'.format(widthName,*width))
        # build model
        ws.factory("BreitWigner::{0}({1}, {2}, {3})".format(label,self.x,meanName,widthName))
        self.params = [meanName,widthName]

class BreitWignerSpline(ModelSpline):

    def __init__(self,name,**kwargs):
        super(BreitWignerSpline,self).__init__(name,**kwargs)

    def build(self,ws,label):
        logging.debug('Building {}'.format(label))
        meanName = 'mean_{0}'.format(label)
        widthName = 'width_{0}'.format(label)
        masses = self.kwargs.get('masses', [])
        means  = self.kwargs.get('means',  [])
        widths = self.kwargs.get('widths', [])
        # splines
        meanSpline  = ROOT.RooSpline1D(meanName,  meanName,  ws.var('MH'), len(masses), array('d',masses), array('d',means))
        widthSpline = ROOT.RooSpline1D(widthName, widthName, ws.var('MH'), len(masses), array('d',masses), array('d',widths))
        # import
        getattr(ws, "import")(meanSpline, ROOT.RooFit.RecycleConflictNodes())
        getattr(ws, "import")(widthSpline, ROOT.RooFit.RecycleConflictNodes())
        # build model
        ws.factory("BreitWigner::{0}({1}, {2}, {3})".format(label,self.x,meanName,widthName))
        self.params = [meanName,widthName]

class Voigtian(Model):

    def __init__(self,name,**kwargs):
        super(Voigtian,self).__init__(name,**kwargs)

    def build(self,ws,label):
        logging.debug('Building {}'.format(label))
        meanName = 'mean_{0}'.format(label)
        widthName = 'width_{0}'.format(label)
        sigmaName = 'sigma_{0}'.format(label)
        mean  = self.kwargs.get('mean',  [1,0,1000])
        width = self.kwargs.get('width', [1,0,100])
        sigma = self.kwargs.get('sigma', [1,0,100])
        # variables
        ws.factory('{0}[{1}, {2}, {3}]'.format(meanName,*mean))
        ws.factory('{0}[{1}, {2}, {3}]'.format(widthName,*width))
        ws.factory('{0}[{1}, {2}, {3}]'.format(sigmaName,*sigma))
        # build model
        ws.factory("Voigtian::{0}({1}, {2}, {3}, {4})".format(label,self.x,meanName,widthName,sigmaName))
        self.params = [meanName,widthName,sigmaName]

class VoigtianSpline(ModelSpline):

    def __init__(self,name,**kwargs):
        super(VoigtianSpline,self).__init__(name,**kwargs)

    def build(self,ws,label):
        logging.debug('Building {}'.format(label))
        meanName = 'mean_{0}'.format(label)
        widthName = 'width_{0}'.format(label)
        sigmaName = 'sigma_{0}'.format(label)
        masses = self.kwargs.get('masses', [])
        means  = self.kwargs.get('means',  [])
        widths = self.kwargs.get('widths', [])
        sigmas = self.kwargs.get('sigmas', [])
        # splines
        meanSpline  = ROOT.RooSpline1D(meanName,  meanName,  ws.var('MH'), len(masses), array('d',masses), array('d',means))
        widthSpline = ROOT.RooSpline1D(widthName, widthName, ws.var('MH'), len(masses), array('d',masses), array('d',widths))
        sigmaSpline = ROOT.RooSpline1D(sigmaName, sigmaName, ws.var('MH'), len(masses), array('d',masses), array('d',sigmas))
        # import
        getattr(ws, "import")(meanSpline, ROOT.RooFit.RecycleConflictNodes())
        getattr(ws, "import")(widthSpline, ROOT.RooFit.RecycleConflictNodes())
        getattr(ws, "import")(sigmaSpline, ROOT.RooFit.RecycleConflictNodes())
        # build model
        ws.factory("Voigtian::{0}({1}, {2}, {3}, {4})".format(label,self.x,meanName,widthName,sigmaName))
        self.params = [meanName,widthName,sigmaName]

class CrystalBall(Model):

    def __init__(self,name,**kwargs):
        super(CrystalBall,self).__init__(name,**kwargs)

    def build(self,ws,label):
        logging.debug('Building {}'.format(label))
        meanName = 'mean_{0}'.format(label)
        sigmaName = 'sigma_{0}'.format(label)
        aName = 'a_{0}'.format(label)
        nName = 'n_{0}'.format(label)
        mean  = self.kwargs.get('mean',  [1,0,1000])
        width = self.kwargs.get('width', [1,0,100])
        sigma = self.kwargs.get('sigma', [1,0,100])
        a     = self.kwargs.get('a', [1,0,100])
        n     = self.kwargs.get('n', [1,0,100])
        # variables
        ws.factory('{0}[{1}, {2}, {3}]'.format(meanName,*mean))
        ws.factory('{0}[{1}, {2}, {3}]'.format(sigmaName,*sigma))
        ws.factory('{0}[{1}, {2}, {3}]'.format(aName,*a))
        ws.factory('{0}[{1}, {2}, {3}]'.format(nName,*n))
        # build model
        ws.factory("RooCBShape::{0}({1}, {2}, {3}, {4}, {5})".format(label,self.x,meanName,sigmaName,aName,nName))
        self.params = [meanName,sigmaName,aName,nName]

class CrystalBallSpline(ModelSpline):

    def __init__(self,name,**kwargs):
        super(CrystalBallSpline,self).__init__(name,**kwargs)

    def build(self,ws,label):
        logging.debug('Building {}'.format(label))
        meanName = 'mean_{0}'.format(label)
        sigmaName = 'sigma_{0}'.format(label)
        aName = 'a_{0}'.format(label)
        nName = 'n_{0}'.format(label)
        masses = self.kwargs.get('masses', [])
        means  = self.kwargs.get('means',  [])
        sigmas = self.kwargs.get('sigmas', [])
        a_s = self.kwargs.get('a_s', [])
        n_s = self.kwargs.get('n_s', [])
        # splines
        meanSpline  = ROOT.RooSpline1D(meanName,  meanName,  ws.var('MH'), len(masses), array('d',masses), array('d',means))
        sigmaSpline = ROOT.RooSpline1D(sigmaName, sigmaName, ws.var('MH'), len(masses), array('d',masses), array('d',sigmas))
        aSpline =     ROOT.RooSpline1D(aName, aName, ws.var('MH'), len(masses), array('d',masses), array('d',a_s))
        nSpline =     ROOT.RooSpline1D(nName, nName, ws.var('MH'), len(masses), array('d',masses), array('d',n_s))
        # import
        getattr(ws, "import")(meanSpline, ROOT.RooFit.RecycleConflictNodes())
        getattr(ws, "import")(sigmaSpline, ROOT.RooFit.RecycleConflictNodes())
        getattr(ws, "import")(aSpline, ROOT.RooFit.RecycleConflictNodes())
        getattr(ws, "import")(nSpline, ROOT.RooFit.RecycleConflictNodes())
        # build model
        ws.factory("RooCBShape::{0}({1}, {2}, {3}, {4}, {5})".format(label,self.x,meanName,sigmaName,aName,nName))
        self.params = [meanName,sigmaName,aName,nName]

class DoubleCrystalBall(Model):

    def __init__(self,name,**kwargs):
        super(DoubleCrystalBall,self).__init__(name,**kwargs)
        if not hasattr(ROOT,"DoubleCrystalBall"):
            ROOT.gROOT.ProcessLine(".L /afs/cern.ch/work/k/ktos/public/Plotting/CMSSW_8_1_0/src/CombineLimits/Limits/macros/DoubleCrystalBall.cpp")        
        

    def build(self,ws,label):
        logging.debug('Building {}'.format(label))
        meanName = 'mean_{0}'.format(label)
        sigmaName = 'sigma_{0}'.format(label)
        a1Name = 'a1_{0}'.format(label)
        n1Name = 'n1_{0}'.format(label)
        a2Name = 'a2_{0}'.format(label)
        n2Name = 'n2_{0}'.format(label)
        mean  = self.kwargs.get('mean',  [1,0,1000])
        sigma = self.kwargs.get('sigma', [1,0,100])
        a1     = self.kwargs.get('a1', [1,0,100])
        n1     = self.kwargs.get('n1', [1,0,100])
        a2     = self.kwargs.get('a2', [1,0,100])
        n2     = self.kwargs.get('n2', [1,0,100])    
        # variables
        ws.factory('{0}[{1}, {2}, {3}]'.format(meanName,*mean))
        ws.factory('{0}[{1}, {2}, {3}]'.format(sigmaName,*sigma))
        ws.factory('{0}[{1}, {2}, {3}]'.format(a1Name,*a1))
        ws.factory('{0}[{1}, {2}, {3}]'.format(n1Name,*n1))
        ws.factory('{0}[{1}, {2}, {3}]'.format(a2Name,*a2))
        ws.factory('{0}[{1}, {2}, {3}]'.format(n2Name,*n2))

        # build model
        doubleCB = ROOT.DoubleCrystalBall(label, label, ws.arg(self.x), ws.arg(meanName), ws.arg(sigmaName), 
                   ws.arg(a1Name), ws.arg(n1Name), ws.arg(a2Name), ws.arg(n2Name) )
        self.wsimport(ws, doubleCB)
        self.params = [meanName,sigmaName,a1Name,n1Name,a2Name,n2Name]

class DoubleCrystalBallSpline(ModelSpline):

    def __init__(self,name,**kwargs):
        super(DoubleCrystalBallSpline,self).__init__(name,**kwargs)
        if not hasattr(ROOT,"DoubleCrystalBall"):
            ROOT.gROOT.ProcessLine(".L /afs/cern.ch/work/k/ktos/public/Plotting/CMSSW_8_1_0/src/CombineLimits/Limits/macros/DoubleCrystalBall.cpp")

    def build(self,ws,label):
        print "CHECK1"
        logging.debug('Building {}'.format(label))
        meanName = 'mean_{0}'.format(label)
        sigmaName = 'sigma_{0}'.format(label)
        a1Name = 'a1_{0}'.format(label)
        n1Name = 'n1_{0}'.format(label)
        a2Name = 'a2_{0}'.format(label)
        n2Name = 'n2_{0}'.format(label)
        masses = self.kwargs.get('masses', [])
        means  = self.kwargs.get('means',  [])
        sigmas = self.kwargs.get('sigmas', [])
        a1s = self.kwargs.get('a1s', [])
        n1s = self.kwargs.get('n1s', [])
        a2s = self.kwargs.get('a2s', [])
        n2s = self.kwargs.get('n2s', [])
        print "CHECK2"
        # splines
        meanSpline  = ROOT.RooSpline1D(meanName,  meanName,  ws.var('MH'), len(masses), array('d',masses), array('d',means))
        sigmaSpline = ROOT.RooSpline1D(sigmaName, sigmaName, ws.var('MH'), len(masses), array('d',masses), array('d',sigmas))
        a1Spline =     ROOT.RooSpline1D(a1Name, a1Name, ws.var('MH'), len(masses), array('d',masses), array('d',a1s))
        n1Spline =     ROOT.RooSpline1D(n1Name, n1Name, ws.var('MH'), len(masses), array('d',masses), array('d',n1s))
        a2Spline =     ROOT.RooSpline1D(a2Name, a2Name, ws.var('MH'), len(masses), array('d',masses), array('d',a2s))
        n2Spline =     ROOT.RooSpline1D(n2Name, n2Name, ws.var('MH'), len(masses), array('d',masses), array('d',n2s))
        print "CHECK3"
        # import
        getattr(ws, "import")(meanSpline, ROOT.RooFit.RecycleConflictNodes())
        getattr(ws, "import")(sigmaSpline, ROOT.RooFit.RecycleConflictNodes())
        getattr(ws, "import")(a1Spline, ROOT.RooFit.RecycleConflictNodes())
        getattr(ws, "import")(n1Spline, ROOT.RooFit.RecycleConflictNodes())
        getattr(ws, "import")(a2Spline, ROOT.RooFit.RecycleConflictNodes())
        getattr(ws, "import")(n2Spline, ROOT.RooFit.RecycleConflictNodes())
        print "CHECK4"

        # build model
        doubleCB = ROOT.DoubleCrystalBall(label, label, ws.arg(self.x), ws.arg(meanName), ws.arg(sigmaName), 
                   ws.arg(a1Name), ws.arg(n1Name), ws.arg(a2Name), ws.arg(n2Name) )
        print  "DOUBLECV", doubleCB.Print()
        self.wsimport(ws, doubleCB)
        self.params = [meanName,sigmaName,a1Name,n1Name,a2Name,n2Name]

class DoubleSidedGaussian(Model):

    def __init__(self,name,**kwargs):
        super(DoubleSidedGaussian,self).__init__(name,**kwargs)
        if not hasattr(ROOT,"DoubleSidedGaussian"):
            ROOT.gROOT.ProcessLine(".L /afs/cern.ch/work/k/ktos/public/Plotting/CMSSW_8_1_0/src/CombineLimits/Limits/macros/DoubleSidedGaussian.cpp")        
        

    def build(self,ws,label):
        logging.debug('Building {}'.format(label))
        meanName = 'mean_{0}'.format(label)
        sigma1Name = 'sigma1_{0}'.format(label)
        sigma2Name = 'sigma2_{0}'.format(label)
        mean  = self.kwargs.get('mean',  [1,0,1000])
        sigma1 = self.kwargs.get('sigma1', [1,0,100])
        sigma2 = self.kwargs.get('sigma2', [1,0,100])
        yMax = self.kwargs.get('yMax')
        # variables
        ws.factory('{0}[{1}, {2}, {3}]'.format(meanName,*mean))
        ws.factory('{0}[{1}, {2}, {3}]'.format(sigma1Name,*sigma1))
        ws.factory('{0}[{1}, {2}, {3}]'.format(sigma2Name,*sigma2))

        # build model
        doubleG = ROOT.DoubleSidedGaussian(label, label, ws.arg(self.x), ws.arg(meanName), ws.arg(sigma1Name), ws.arg(sigma2Name), yMax )
        self.wsimport(ws, doubleG)
        self.params = [meanName,sigma1Name,sigma2Name]

class DoubleSidedGaussianSpline(ModelSpline):

    def __init__(self,name,**kwargs):
        super(DoubleSidedGaussianSpline,self).__init__(name,**kwargs)
        if not hasattr(ROOT,"DoubleSidedGaussian"):
            ROOT.gROOT.ProcessLine(".L /afs/cern.ch/work/k/ktos/public/Plotting/CMSSW_8_1_0/src/CombineLimits/Limits/macros/DoubleSidedGaussian.cpp")

    def build(self,ws,label):
        logging.debug('Building {}'.format(label))
        meanName = 'mean_{0}'.format(label)
        sigma1Name = 'sigma1_{0}'.format(label)
        sigma2Name = 'sigma2_{0}'.format(label)
        masses = self.kwargs.get('masses', [])
        means  = self.kwargs.get('means',  [])
        sigma1s = self.kwargs.get('sigma1s', [])
        sigma2s = self.kwargs.get('sigma2s', [])
        yMax = self.kwargs.get('yMax')
        # splines
        meanSpline  = ROOT.RooSpline1D(meanName,  meanName,  ws.var('MH'), len(masses), array('d',masses), array('d',means))
        sigma1Spline = ROOT.RooSpline1D(sigma1Name, sigma1Name, ws.var('MH'), len(masses), array('d',masses), array('d',sigma1s))
        sigma2Spline = ROOT.RooSpline1D(sigma2Name, sigma2Name, ws.var('MH'), len(masses), array('d',masses), array('d',sigma2s))
        # import
        getattr(ws, "import")(meanSpline, ROOT.RooFit.RecycleConflictNodes())
        getattr(ws, "import")(sigma1Spline, ROOT.RooFit.RecycleConflictNodes())
        getattr(ws, "import")(sigma2Spline, ROOT.RooFit.RecycleConflictNodes())

        # build model
        doubleG = ROOT.DoubleSidedGaussian(label, label, ws.arg(self.x), ws.arg(meanName), ws.arg(sigma1Name), ws.arg(sigma2Name), yMax )
        self.wsimport(ws, doubleG)
        self.params = [meanName,sigma1Name,sigma2Name] 

class DoubleSidedVoigtian(Model):

    def __init__(self,name,**kwargs):
        super(DoubleSidedVoigtian,self).__init__(name,**kwargs)
        if not hasattr(ROOT,"DoubleSidedVoigtian"):
            ROOT.gROOT.ProcessLine(".L /afs/cern.ch/work/k/ktos/public/Plotting/CMSSW_8_1_0/src/CombineLimits/Limits/macros/DoubleSidedVoigtian.cpp")        
        

    def build(self,ws,label):
        logging.debug('Building {}'.format(label))
        meanName = 'mean_{0}'.format(label)
        sigma1Name = 'sigma1_{0}'.format(label)
        sigma2Name = 'sigma2_{0}'.format(label)
        width1Name = 'width1_{0}'.format(label)
        width2Name = 'width2_{0}'.format(label)
        mean  = self.kwargs.get('mean',  [1,0,1000])
        sigma1 = self.kwargs.get('sigma1', [1,0,100])
        sigma2 = self.kwargs.get('sigma2', [1,0,100])
        width1 = self.kwargs.get('width1', [1,0,100])
        width2 = self.kwargs.get('width2', [1,0,100])
        yMax = self.kwargs.get('yMax')
        # variables
        ws.factory('{0}[{1}, {2}, {3}]'.format(meanName,*mean))
        ws.factory('{0}[{1}, {2}, {3}]'.format(sigma1Name,*sigma1))
        ws.factory('{0}[{1}, {2}, {3}]'.format(sigma2Name,*sigma2))
        ws.factory('{0}[{1}, {2}, {3}]'.format(width1Name,*width1))
        ws.factory('{0}[{1}, {2}, {3}]'.format(width2Name,*width2))

        # build model
        doubleV = ROOT.DoubleSidedVoigtian(label, label, ws.arg(self.x), ws.arg(meanName), ws.arg(sigma1Name), ws.arg(sigma2Name), ws.arg(width1Name), ws.arg(width2Name), yMax )
        self.wsimport(ws, doubleV)
        self.params = [meanName,sigma1Name,sigma2Name,width1Name,width2Name]

class DoubleSidedVoigtianSpline(ModelSpline):

    def __init__(self,name,**kwargs):
        super(DoubleSidedVoigtianSpline,self).__init__(name,**kwargs)
        if not hasattr(ROOT,"DoubleSidedVoigtian"):
            ROOT.gROOT.ProcessLine(".L /afs/cern.ch/work/k/ktos/public/Plotting/CMSSW_8_1_0/src/CombineLimits/Limits/macros/DoubleSidedVoigtian.cpp")

    def build(self,ws,label):
        logging.debug('Building {}'.format(label))
        meanName = 'mean_{0}'.format(label)
        sigma1Name = 'sigma1_{0}'.format(label)
        sigma2Name = 'sigma2_{0}'.format(label)
        width1Name = 'width1_{0}'.format(label)
        width2Name = 'width2_{0}'.format(label)
        masses = self.kwargs.get('masses', [])
        means  = self.kwargs.get('means',  [])
        sigma1s = self.kwargs.get('sigma1s', [])
        sigma2s = self.kwargs.get('sigma2s', [])
        width1s = self.kwargs.get('width1s', [])
        width2s = self.kwargs.get('width2s', [])  
        yMax = self.kwargs.get('yMax')
        # splines
        meanSpline  = ROOT.RooSpline1D(meanName,  meanName,  ws.var('MH'), len(masses), array('d',masses), array('d',means))
        sigma1Spline = ROOT.RooSpline1D(sigma1Name, sigma1Name, ws.var('MH'), len(masses), array('d',masses), array('d',sigma1s))
        sigma2Spline = ROOT.RooSpline1D(sigma2Name, sigma2Name, ws.var('MH'), len(masses), array('d',masses), array('d',sigma2s))
        width1Spline = ROOT.RooSpline1D(width1Name, width1Name, ws.var('MH'), len(masses), array('d',masses), array('d',width1s))
        width2Spline = ROOT.RooSpline1D(width2Name, width2Name, ws.var('MH'), len(masses), array('d',masses), array('d',width2s))
        # import
        getattr(ws, "import")(meanSpline, ROOT.RooFit.RecycleConflictNodes())
        getattr(ws, "import")(sigma1Spline, ROOT.RooFit.RecycleConflictNodes())
        getattr(ws, "import")(sigma2Spline, ROOT.RooFit.RecycleConflictNodes())
        getattr(ws, "import")(width1Spline, ROOT.RooFit.RecycleConflictNodes())
        getattr(ws, "import")(width2Spline, ROOT.RooFit.RecycleConflictNodes())

        # build model
        doubleV = ROOT.DoubleSidedVoigtian(label, label, ws.arg(self.x), ws.arg(meanName), ws.arg(sigma1Name), ws.arg(sigma2Name), ws.arg(width1Name), ws.arg(width2Name), yMax )
        self.wsimport(ws, doubleV)
        self.params = [meanName,sigma1Name,sigma2Name,width1Name,width2Name] 

class Exponential(Model):

    def __init__(self,name,**kwargs):
        super(Exponential,self).__init__(name,**kwargs)

    def build(self,ws,label):
        logging.debug('Building {}'.format(label))
        lambdaName = 'lambda_{0}'.format(label)
        lamb = self.kwargs.get('lamb',  [-1,-5,0])
        # variables
        ws.factory('{0}[{1}, {2}, {3}]'.format(lambdaName,*lamb))
        # build model
        ws.factory("Exponential::{0}({1}, {2})".format(label,self.x,lambdaName))
        self.params = [lambdaName]

class Erf(Model):

    def __init__(self,name,**kwargs):
        super(Erf,self).__init__(name,**kwargs)

    def build(self,ws,label):
        logging.debug('Building {}'.format(label))
        erfScaleName = 'erfScale_{0}'.format(label)
        erfShiftName = 'erfShift_{0}'.format(label)
        erfScale = self.kwargs.get('erfScale', [1,0,10])
        erfShift = self.kwargs.get('erfShift', [0,0,100])
        # variables
        ws.factory('{0}[{1}, {2}, {3}]'.format(erfScaleName,*erfScale))
        ws.factory('{0}[{1}, {2}, {3}]'.format(erfShiftName,*erfShift))
        print 'ERFSCALE {0}[{1}, {2}, {3}]'.format(erfScaleName,*erfScale)
        print 'ERFSHIFT {0}[{1}, {2}, {3}]'.format(erfShiftName,*erfShift)
        # build model
        ws.factory("EXPR::{0}('0.5*(TMath::Erf({2}*({1}-{3}))+1)', {1}, {2}, {3})".format(
            label,self.x,erfScaleName,erfShiftName)
        )
        self.params = [erfScaleName,erfShiftName]

class ErfSpline(ModelSpline):
        
    def __init__(self,name,**kwargs):
        super(ErfSpline,self).__init__(name,**kwargs)
    
    def build(self,ws,label):
        logging.debug('Building {}'.format(label))
        erfScaleName = 'erfScale_{0}'.format(label)
        erfShiftName = 'erfShift_{0}'.format(label)
        masses = self.kwargs.get('masses', [])
        erfScales  = self.kwargs.get('erfScales',  [])
        erfShifts = self.kwargs.get('erfShifts', [])
        # splines  
        erfScaleSpline  = ROOT.RooSpline1D(erfScaleName,  erfScaleName,  ws.var('MH'), len(masses), array('d',masses), array('d',erfScales))
        erfShiftSpline = ROOT.RooSpline1D(erfShiftName, erfShiftName, ws.var('MH'), len(masses), array('d',masses), array('d',erfShifts))
        # import
        getattr(ws, "import")(erfScaleSpline, ROOT.RooFit.RecycleConflictNodes())
        getattr(ws, "import")(erfShiftSpline, ROOT.RooFit.RecycleConflictNodes())
        # build model
        ws.factory("EXPR::{0}('0.5*(TMath::Erf({2}*({1}-{3}))+1)', {1}, {2}, {3})".format(
                   label,self.x,erfScaleName,erfShiftName)
        )
        self.params = [erfScaleName,erfShiftName]

class Sum(Model):

    def __init__(self,name,**kwargs):
        self.doRecursive = kwargs.pop('recursive',False)
        self.doExtended = kwargs.pop('extended',False)
        super(Sum,self).__init__(name,**kwargs)

    #def recurse(self,curr,remaining):
    #    if len(remaining):
    #        return '{0}_frac*{0} + (1-{0}_frac)*({2})'.format(curr,self.recurse(remaining[0],remaining[1:]))
    #    else:
    #        return '{0}_frac*{0}'.format(curr)

    def build(self,ws,label):
        logging.debug('Building {}'.format(label))
        pdfs = []
        sumpdfs = []
        for n, (pdf, r) in enumerate(sorted(self.kwargs.iteritems())):
            if len(r)==2:
                ws.factory('{0}_frac[{1},{2}]'.format(pdf,*r))
                sumpdfs += [pdf]
            elif len(r)==3:
                ws.factory('{0}_frac[{1},{2},{3}]'.format(pdf,*r))
                sumpdfs += [pdf]
            pdfs += [pdf]
        pdf = sorted(pdfs)
        # build model
        if self.doRecursive:
            sumargs = ['{0}_frac*{0}'.format(pdf) for pdf in pdfs[:-1]] + [pdfs[-1]]
            ws.factory("RSUM::{0}({1})".format(label, ', '.join(sumargs)))
        elif self.doExtended:
            sumargs = ['{0}_frac*{0}'.format(pdf) for pdf in pdfs]
            ws.factory("SUM::{0}({1})".format(label, ', '.join(sumargs)))
        else: # Don't do this if you have more than 2 pdfs ...
            if len(sumpdfs)>1: logging.warning('This sum is not guaranteed to be positive because there are more than two arguments. Better to use the option recursive=True.')
            sumargs = ['{0}_frac*{0}'.format(pdf) for pdf in sumpdfs[:-1]] + [sumpdfs[-1]]
            ws.factory("SUM::{0}({1})".format(label, ', '.join(sumargs)))
        self.params = ['{}_frac'.format(pdf) for pdf in pdfs]

class Prod(Model):

    def __init__(self,name,*args,**kwargs):
        super(Prod,self).__init__(name,**kwargs)
        self.args = args

    def build(self,ws,label):
        logging.debug('Building {}'.format(label))
        ws.factory("PROD::{0}({1})".format(label, ', '.join(self.args)))
        self.params = []

class ProdSpline(ModelSpline):

    def __init__(self,name,*args,**kwargs):
        super(ProdSpline,self).__init__(name,**kwargs)
        self.args = args

    def build(self,ws,label):
        logging.debug('Building {}'.format(label))
        ws.factory("PROD::{0}({1})".format(label, ', '.join(self.args)))
        self.params = []
